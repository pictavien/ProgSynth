import glob
import os
import argparse
import sys

import numpy as np

from experiments.sygus_parser import HackerDelightParser
from synth.specification import Example, PBEWithConstants
from synth.syntax import auto_type
from synth.task import Dataset, Task

from examples.pbe.sygus.bitvectors import dsl, evaluator


parser = argparse.ArgumentParser()
parser.add_argument("folder", type=str, help="folder from which to load SyGus files")

parameters = parser.parse_args(sys.argv[1:])

np.random.seed(5646546)

folder: str = parameters.folder
if not folder.endswith("/"):
    folder += "/"
tasks = []

for file in glob.glob(folder + "*.sl"):
    task_name = os.path.basename(file)
    print(task_name)
    specification_parser = HackerDelightParser(file)
    specifications = specification_parser.parse()
    var_names = specifications[0]
    str_type = ["bv"] * len(var_names)
    solution = specification_parser.solution

    # Parse Type Request
    tr = auto_type(" -> ".join(str_type + [specification_parser.dst]))
    # print("\t", tr)
    constants = {
        x: (auto_type("bv"), int(x[2:], 16))
        for x in specification_parser.constants
        if dsl.get_primitive(x) is None
    }
    # print("\tconstants:", constants)
    cst_values = [x[1] for x in constants.values()]
    solution = dsl.parse_program(
        specification_parser.solution, tr.returns(), constants=constants
    )
    # Generate Examples
    examples = []
    output_set = set()
    for i in range(10):
        inputs = []
        for _ in tr.arguments():
            x = int(
                np.random.randint((1 << 63) - 1) * np.random.choice(np.array([-1, 1]))
            )
            inputs.append(x)
        output = evaluator.eval(solution, inputs)
        # print("\tinputs=", inputs)
        # print("\toutput=", output)
        output_set.add(output)
        examples.append(Example(inputs, output))
    if len(output_set) == 1:
        print("\tskipped because could not generate relevant examples.")
        continue
    # Create task
    task = Task[PBEWithConstants](
        tr,
        specification=PBEWithConstants(examples, {auto_type("bv"): cst_values}),
        solution=solution,
        metadata={"name": task_name[:-3]},
    )
    tasks.append(task)
name = "bitvectors"
Dataset(tasks).save(f"./sygus_{name}.pickle")
