import argparse
from collections import defaultdict
from typing import Any, Callable, Tuple, List
from dsl_loader import add_dsl_choice_arg, load_DSL
import tqdm

from synth import Dataset, PBE
from synth.pbe.task_generator import TaskGenerator
from synth.syntax.program import Program
from synth.utils import chrono
from synth.syntax import CFG

DREAMCODER = "dreamcoder"
REGEXP = "regexp"
CALCULATOR = "calculator"
TRANSDUCTION = "transduction"


parser = argparse.ArgumentParser(
    description="Generate a dataset copying the original distribution of another dataset"
)
add_dsl_choice_arg(parser)

parser.add_argument(
    "--dataset",
    type=str,
    default="{dsl_name}.pickle",
    help="dataset file (default: {dsl_name}.pickle)",
)
parser.add_argument(
    "-o",
    "--output",
    type=str,
    default="dataset.pickle",
    help="output file (default: dataset.pickle)",
)
parser.add_argument("-s", "--seed", type=int, default=0, help="seed (default: 0)")
parser.add_argument(
    "--programs", type=int, default=50, help="generated programs (default: 100)"
)
parser.add_argument(
    "--inputs", type=int, default=20, help="generated inputs (default: 20)"
)
parser.add_argument(
    "--max-depth", type=int, default=5, help="solutions max depth (default: 5)"
)
parser.add_argument(
    "--uniform", action="store_true", default=False, help="use uniform PCFGs"
)
parser.add_argument(
    "--no-unique",
    action="store_true",
    default=False,
    help="does not try to generate unique tasks",
)
parser.add_argument(
    "--constrained",
    action="store_true",
    default=False,
    help="tries to add constraints of the DSL to the grammar",
)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    default=False,
    help="verbose generation",
)
parameters = parser.parse_args()
dsl_name: str = parameters.dsl
dataset_file: str = parameters.dataset.format(dsl_name=dsl_name)
output_file: str = parameters.output
seed: int = parameters.seed
max_depth: int = parameters.max_depth
nb_programs: int = parameters.programs
nb_inputs: int = parameters.inputs
uniform: bool = parameters.uniform
no_unique: bool = parameters.no_unique
constrained: bool = parameters.constrained
verbose: bool = parameters.verbose

# ================================
# Load constants specific to DSL
# ================================
max_list_length = None
dsl_module = load_DSL(dsl_name)
dsl, evaluator, lexicon = dsl_module.dsl, dsl_module.evaluator, dsl_module.lexicon

if hasattr(dsl_module, "reproduce_dataset"):
    reproduce_dataset = dsl_module.reproduce_dataset
else:
    from synth.pbe.task_generator import reproduce_int_dataset as reproduce_dataset

constraints = []
if hasattr(dsl_module, "constraints") and constrained:
    constraints = dsl_module.constraints

if dsl_name == DREAMCODER:
    max_list_length = 10

# ================================
# Load dataset & Task Generator
# ================================
# Load dataset
print(f"Loading {dataset_file}...", end="")
with chrono.clock("dataset.load") as c:
    full_dataset: Dataset[PBE] = Dataset.load(dataset_file)
    print("done in", c.elapsed_time(), "s")
# Reproduce dataset distribution
print("Reproducing dataset...", end="", flush=True)
with chrono.clock("dataset.reproduce") as c:
    task_generator, lexicon = reproduce_dataset(
        full_dataset,
        dsl,
        evaluator,
        seed,
        max_list_length=max_list_length,
        default_max_depth=max_depth,
        uniform_pgrammar=uniform,
        constraints=constraints,
        verbose=verbose,
    )
    cfgs = task_generator.type2pgrammar
    if constrained:
        cfgs = {
            t: CFG.depth_constraint(dsl, t, max_depth, min_variable_depth=0)
            for t in task_generator.type2pgrammar
        }
    print("done in", c.elapsed_time(), "s")
# Add some exceptions that are ignored during task generation
task_generator.skip_exceptions.add(TypeError)
task_generator.uniques = not no_unique
task_generator.verbose = True

#
def generate_samples_for(
    programs: List[Program],
    input_sampler: Callable[[], Any],
    eval_prog: Callable[[Program, Any], Any],
    clear_cache: Callable,
    threshold: int = 1000,
    examples: int = 5,
) -> Tuple[List, List[Program]]:
    samples = []
    equiv_classes = {None: programs}
    i = 1
    n = 0
    pbar = tqdm.tqdm(total=examples - 1)
    # Nice try
    best = None
    best_score = 0
    while 2 * len(equiv_classes) < len(programs) and i < examples:
        next_equiv_classes = defaultdict(list)
        clear_cache()
        if n > threshold:
            ui = best
        else:
            ui = input_sampler()
        for cl, prog in equiv_classes.items():
            for p in prog:
                o = eval_prog(p, ui)
                if isinstance(o, List):
                    o = tuple(o)
                next_equiv_classes[(o, cl)].append(p)
        ratio = len(next_equiv_classes) / len(equiv_classes)
        if len(next_equiv_classes) > best_score:
            best = ui
            best_score = len(next_equiv_classes)
        if (
            n > threshold
            or len(next_equiv_classes) * (ratio ** (examples - i)) >= len(programs) / 2
        ):
            i += 1
            pbar.update(1)
            equiv_classes = next_equiv_classes
            samples.append(ui)
            n = 0
            best_score = len(next_equiv_classes)
        else:
            pbar.set_postfix_str(
                f"{n} tested/ {len(next_equiv_classes)} from {len(equiv_classes)}({len(programs)})"
            )
        n += 1
        # pbar.set_postfix_str(f"{n} tested")
    # Brute try
    pbar.close()
    to_keep = [
        min([(p.length(), p) for p in v], key=lambda x: x[0])[1]
        for v in equiv_classes.values()
    ]
    return samples, to_keep


#

print("Generating programs...", nb_programs, end="", flush=True)
type_requests = set()
with chrono.clock("dataset.generate.programs") as c:
    programs = []
    programs_by_tr = defaultdict(list)
    assert isinstance(task_generator, TaskGenerator)
    for i in tqdm.trange(2 * nb_programs, desc="programs generated"):
        tr = task_generator.generate_type_request()
        prog, unique = task_generator.generate_program(tr)
        while not no_unique and not unique:
            tr = task_generator.generate_type_request()
            prob, unique = task_generator.generate_program(tr)
        type_requests.add(tr)
        programs_by_tr[tr].append(prog)
        programs.append((tr, prog))
    print("done in", c.elapsed_time(), "s")
print("Generating inputs...", nb_inputs, end="", flush=True)

filtered_programs = []
with chrono.clock("dataset.generate.inputs") as c:
    inputs = {}
    for tr in type_requests:
        inputs[tr] = []
        args = tr.arguments()
        assert isinstance(task_generator, TaskGenerator)
        for i in tqdm.trange(nb_inputs, desc=f"inputs generated for {tr}"):
            sample, to_keep = generate_samples_for(
                programs_by_tr[tr],
                lambda: task_generator.sample_input(args),
                lambda p, x: task_generator.eval_input(p, x),
                task_generator.evaluator.clear_cache,
            )
            inputs[tr].append(sample)
            for p in to_keep:
                filtered_programs.append((tr, p))
    print("done in", c.elapsed_time(), "s")
    print("Kept", len(filtered_programs), "/", len(programs), "programs")

print("Evaluating inputs...", end="", flush=True)
with chrono.clock("dataset.evaluation.inputs") as c:
    tasks = []
    for tr, program in tqdm.tqdm(filtered_programs, desc="programs evaluated"):
        for sample in inputs[tr]:
            tasks.append(
                task_generator.make_task(
                    tr,
                    program,
                    sample,
                    [task_generator.eval_input(program, x) for x in sample],
                )
            )

    print("done in", c.elapsed_time(), "s")
gen_dataset = Dataset(tasks)
print("Saving dataset...", end="", flush=True)
with chrono.clock("dataset.save") as c:
    gen_dataset.save(output_file)
    print("done in", c.elapsed_time(), "s")

# ================================
# Print some stats
# ================================
# Generate the CFG dictionnary
all_type_requests = gen_dataset.type_requests()
print(f"{len(all_type_requests)} type requests supported.")
print(f"Lexicon: [{min(lexicon)};{max(lexicon)}]")
