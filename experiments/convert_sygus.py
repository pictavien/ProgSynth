import glob
import os
import argparse
import sys

from experiments.sygus_parser import StrParser, BvParser
from synth.specification import Example, PBEWithConstants
from synth.syntax import auto_type, guess_type
from synth.task import Dataset, Task


parser = argparse.ArgumentParser()
parser.add_argument("folder", type=str, help="folder from which to load SyGus files")
parser.add_argument("-bv", action="store_true", help="bit vectors")

parameters = parser.parse_args(sys.argv[1:])


folder: str = parameters.folder
if not folder.endswith("/"):
    folder += "/"
BV: bool = parameters.bv
tasks = []

for file in glob.glob(folder + "*.sl"):
    task_name = os.path.basename(file)
    print(task_name)
    constants = {}
    if BV:
        specification_parser = BvParser(file)
        specifications = specification_parser.parse()
        var_names = specifications[0]
        str_type = ["bv"] * len(var_names)
    else:
        specification_parser = StrParser(file)
        specifications = specification_parser.parse()
        string_variables = specifications[0]
        string_literals = specifications[1]
        integer_variables = specifications[2]
        integer_literals = specifications[3]
        examples_data = specifications[4]
        var_names = string_variables + integer_variables
        constants = {
            auto_type("int"): integer_literals,
            auto_type("string"): string_literals,
        }
        str_type = ["string"] * len(string_variables) + ["int"] * len(integer_variables)

    # Parse examples
    examples = []
    guessed = None
    for example in specifications[-2]:
        inputs = []
        for name in var_names:
            inputs.append(example[name])
        ex = Example(inputs, example["out"])
        if ex not in examples:
            examples.append(ex)
            guessed = guess_type(example["out"])
    assert guessed

    # Parse Type Request
    tr = auto_type(" -> ".join(str_type + [str(guessed)]))
    print("\t", tr)
    # Create task
    task = Task[PBEWithConstants](
        tr,
        specification=PBEWithConstants(examples, constants),
        metadata={"name": task_name[:-3]},
    )
    tasks.append(task)
name = "strings" if not BV else "bitvectors"
Dataset(tasks).save(f"./sygus_{name}.pickle")
