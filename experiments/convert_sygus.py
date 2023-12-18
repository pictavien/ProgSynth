import glob
import os

from experiments.sygus_parser import StrParser
from synth.specification import Example, PBEWithConstants
from synth.syntax import FunctionType, auto_type, guess_type
from synth.task import Dataset, Task


folder = "../BeeSearch/sygus_string_tasks/"

tasks = []

for file in glob.glob(folder + "*.sl"):
    task_name = os.path.basename(file)
    print(task_name)
    specification_parser = StrParser(file)
    specifications = specification_parser.parse()
    string_variables = specifications[0]
    string_literals = specifications[1]
    integer_variables = specifications[2]
    integer_literals = specifications[3]

    # Parse examples
    examples = []
    guessed = None
    for example in specifications[4]:
        inputs = []
        for name in string_variables:
            inputs.append(example[name])
        for name in integer_variables:
            inputs.append(example[name])
        ex = Example(inputs, example["out"])
        if ex not in examples:
            examples.append(ex)
            guessed = guess_type(example["out"])
    assert guessed

    # Parse Type Request
    tr = FunctionType(
        auto_type(
            "->".join(
                ["string"] * len(string_variables) + ["int"] * len(integer_variables)
            )
        ),
        guessed,
    )
    # constants
    constants = {auto_type("int"): integer_literals, auto_type("str"): string_literals}
    # Create task
    task = Task[PBEWithConstants](
        tr,
        specification=PBEWithConstants(examples, constants),
        metadata={"src": task_name},
    )
    tasks.append(task)

Dataset(tasks).save("./sygus_strings.pickle")
