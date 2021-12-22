from synth.syntax.concrete.concrete_cfg import ConcreteCFG
from synth.syntax.concrete.concrete_pcfg import ConcretePCFG
from synth.semantic.evaluator import DSLEvaluator, __tuplify__
from synth.syntax.dsl import DSL
from synth.syntax.type_system import (
    INT,
    STRING,
    FunctionType,
    List,
    PolymorphicType,
    PrimitiveType,
)


syntax = {
    "+1": FunctionType(INT, INT),
    "head": FunctionType(List(PolymorphicType("a")), PolymorphicType("a")),
    "non_reachable": PrimitiveType("non_reachable"),
    "non_productive": FunctionType(INT, STRING),
}

semantics = {
    "+1": lambda x: x + 1,
}
max_depth = 4
dsl = DSL(syntax)
cfg = ConcreteCFG.from_dsl(dsl, FunctionType(INT, INT), max_depth)


def test_eval() -> None:
    eval = DSLEvaluator(semantics)
    pcfg = ConcretePCFG.uniform_from_cfg(cfg)
    pcfg.init_sampling(0)
    for _ in range(100):
        program = pcfg.sample_program()
        try:
            for i in range(-25, 25):
                assert eval.eval(program, [i]) == program.length() + i - 1
        except Exception as e:
            assert False, e

def test_supports_list() -> None:
    eval = DSLEvaluator(semantics)
    pcfg = ConcretePCFG.uniform_from_cfg(cfg)
    pcfg.init_sampling(0)
    for _ in range(100):
        program = pcfg.sample_program()
        try:
            for i in range(-25, 25):
                assert eval.eval(program, [i, [i]]) == program.length() + i - 1
        except Exception as e:
            assert False, e


def test_use_cache() -> None:
    eval = DSLEvaluator(semantics)
    pcfg = ConcretePCFG.uniform_from_cfg(cfg)
    pcfg.init_sampling(0)
    for _ in range(100):
        program = pcfg.sample_program()
        try:
            for i in range(-25, 25):
                assert eval.eval(program, [i]) == program.length() + i - 1
                assert eval._cache[__tuplify__([i])][program] == program.length() + i - 1
        except Exception as e:
            assert False, e
