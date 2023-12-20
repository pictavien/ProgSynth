from synth.semantic.evaluator import DSLEvaluator
from synth.syntax import DSL, auto_type

from examples.pbe.sygus.task_generator_bitvector import reproduce_bitvector_dataset


__syntax = auto_type(
    {
        "not": "bv -> bv",
        "smol": "bv -> bv",
        "ehad": "bv -> bv",
        "arba": "bv -> bv",
        "shesh": "bv -> bv",
        "and": "bv -> bv -> bv",
        "or": "bv -> bv -> bv",
        "xor": "bv -> bv -> bv",
        "add": "bv -> bv -> bv",
        "ite": "bv -> bv -> bv -> bv",
        "0": "bv",
        "1": "bv",
    }
)

__semantics = {
    "not": lambda x: ~x,
    "smol": lambda x: x << 1,
    "ehad": lambda x: x >> 1,
    "arba": lambda x: x >> 4,
    "shesh": lambda x: x >> 16,
    "and": lambda x: lambda y: x & y,
    "or": lambda x: lambda y: x | y,
    "xor": lambda x: lambda y: x ^ y,
    "add": lambda x: lambda y: x + y,
    "ite": lambda b: lambda x: lambda y: x if b else y,
    "0": 0,
    "1": 1,
}

dsl = DSL(__syntax)
evaluator = DSLEvaluator(dsl.instantiate_semantics(__semantics))
# evaluator.skip_exceptions.add(ZeroDivisionError)
# evaluator.skip_exceptions.add(ValueError)
# evaluator.skip_exceptions.add(TypeError)
# TODO: lexicon
lexicon = list([i for i in range(100000)])
