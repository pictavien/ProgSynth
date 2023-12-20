from typing import (
    Callable,
    Dict,
    List as TList,
    Any,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import numpy as np

from synth.generation.sampler import ListSampler, Sampler
from synth.pbe.task_generator import (
    TaskGenerator,
    __multi_discrete_distribution__,
    __multi_discrete_to_gen__,
)
from synth.syntax.grammars.cfg import CFG
from synth.syntax.grammars.tagged_det_grammar import ProbDetGrammar
from synth.syntax.grammars.tagged_u_grammar import ProbUGrammar
from synth.syntax.program import Program
from synth.syntax.type_system import INT, List, Type
from synth.syntax.type_helper import auto_type

from synth.task import Dataset, Task
from synth.specification import PBE, Example, PBEWithConstants
from synth.semantic.evaluator import DSLEvaluator, DSLEvaluatorWithConstant
from synth.syntax import (
    STRING,
    INT,
    BOOL,
    DSL,
)
from synth.generation import (
    LexiconSampler,
    UnionSampler,
)

np.random.seed(12)

T = TypeVar("T")


def reproduce_dataset(
    dataset: Dataset[PBE],
    dsl: DSL,
    evaluator: DSLEvaluator,
    start: T,
    element_analyser: Callable[[T, Any], T],
    get_element_sampler: Callable[[T], Sampler],
    get_validator: Callable[[T, int], Callable[[Any], bool]],
    get_lexicon: Callable[[T], TList],
    seed: Optional[int] = None,
    max_tries: int = 100,
    default_max_depth: int = 5,
    max_list_length: Optional[int] = None,
    uniform_pgrammar: bool = False,
    constraints: TList[str] = [],
    **kwargs: Any
) -> Tuple[TaskGenerator, TList]:
    """

    start = element_analyser(start, element)
        called when encountering a base element (not a list)
    get_element_sampler(start)
        produces the sampler used for base types (not list)
    get_validator(start, max_list_length)
        produces the output validator
    get_lexicon(start)
        produces the lexicon
    """

    max_depth = -1
    allowed_types: TList[Type] = []
    types_probs_list: TList[float] = []

    list_length: Dict[Type, Dict[int, int]] = {}
    no_samples: Dict[Type, Dict[int, int]] = {}
    max_list_depth = [0]

    out = [start]

    def analyze(element: Any, type: Type, depth: int = 1) -> None:
        if depth > max_list_depth[0]:
            max_list_depth[0] = depth
        if type.is_instance(List):
            elt_type: Type = type.types[0]  # type: ignore
            if len(element) > 0:
                __multi_discrete_distribution__(list_length, type, len(element))
                for el in element:
                    analyze(el, elt_type, depth + 1)
        elif element:
            out[0] = element_analyser(out[0], element)

    # Capture all information in one dataset pass
    for task in dataset:
        if task.solution:
            max_depth = max(max_depth, task.solution.depth())
        # Type distribution
        if task.type_request not in allowed_types:
            allowed_types.append(task.type_request)
            types_probs_list.append(1.0)
        else:
            index = allowed_types.index(task.type_request)
            types_probs_list[index] += 1.0

        # No samples distribution
        __multi_discrete_distribution__(
            no_samples, task.type_request, len(task.specification.examples)
        )

        t = task.type_request
        args = t.arguments()
        r = t.returns()

        # Input data analysis
        for ex in task.specification.examples:
            for input, ti in zip(ex.inputs, args):
                analyze(input, ti)
            analyze(ex.output, r)

    # Type generator
    types_probs = np.array(types_probs_list, dtype=float) / len(dataset)
    type_sampler = LexiconSampler(allowed_types, types_probs, seed)

    list_length_gen = __multi_discrete_to_gen__(
        list_length, seed=seed, maxi=max_list_length
    )
    no_samples_gen = __multi_discrete_to_gen__(no_samples, seed=seed)

    if max_depth == -1:
        max_depth = default_max_depth
    pgrammars: Set[Union[ProbUGrammar, ProbDetGrammar]] = set()
    pgrammars = {
        ProbDetGrammar.uniform(
            CFG.depth_constraint(dsl, t, max_depth, constant_types={INT, STRING})
        )
        for t in allowed_types
    }
    for pgrammar in pgrammars:
        pgrammar.init_sampling(seed)

    input_sampler = ListSampler(
        get_element_sampler(out[0]),
        list_length_gen,
        max_depth=max_list_depth[0],
        seed=seed,
    )

    return (
        TaskGenerator(
            input_sampler,
            evaluator,
            type_sampler,
            no_samples_gen,
            pgrammars,
            get_validator(
                out[0],
                max_list_length
                or max((max(l.keys()) for l in list_length.values()), default=-1)
                or -1,
            ),
            max_tries,
            **kwargs
        ),
        get_lexicon(out[0]),
    )


def reproduce_bitvector_dataset(
    dataset: Dataset[PBE],
    dsl: DSL,
    evaluator: DSLEvaluator,
    seed: Optional[int] = None,
    *args: Any,
    **kwargs: Any
) -> Tuple[TaskGenerator, TList[int]]:
    def analyser(start: Set[int], elment: Any) -> Set[int]:
        start.add(elment)
        return start

    probabilities = np.array([0.5**i for i in range(6)])
    probabilities /= np.sum(probabilities)

    def get_sampler(start: TList[int]) -> UnionSampler:
        return UnionSampler(
            {
                auto_type("bv"): LexiconSampler(list(start), seed=seed),
                BOOL: LexiconSampler([True, False], seed=seed),
            }
        )

    task_generator, lexicon = reproduce_dataset(
        dataset,
        dsl,
        evaluator,
        set(),
        analyser,
        get_sampler,
        lambda _, max_list_length: lambda x: True,
        lambda x: list(x),
        seed,
        *args,
        **kwargs
    )
    lexicon = list(lexicon)

    generator = TaskGenerator(
        task_generator.input_generator,
        task_generator.evaluator,
        task_generator.gen_random_type_request,
        task_generator.gen_random_sample_number,
        task_generator.type2pgrammar.values(),
        task_generator.output_validator,
        task_generator.max_tries,
        task_generator.uniques,
        verbose=task_generator.verbose,
    )

    generator.skip_exceptions.add(ValueError)

    return generator, lexicon
