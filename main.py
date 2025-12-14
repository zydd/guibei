import os
import pprint
import sys

import compiler
import parser
from compiler import codegen

std_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib/prelude")


def main(output_file, input_files):
    code = ""

    std_lib_files = [fname for fname in os.listdir(std_lib_path) if fname.endswith(".gi")]
    # std_lib_files = open(os.path.join(std_lib_path, "prelude"), "r").readlines()
    for filename in std_lib_files:
        with open(os.path.join(std_lib_path, filename), "r", encoding="utf8") as f:
            code += f.read() + "\n"

    for filename in input_files:
        with open(filename, "r", encoding="utf8") as f:
            code += f.read() + "\n"

    prog = parser.parse_str(code)
    if not prog:
        return 1

    module = compiler.semantic_pass(prog)
    with open(output_file + ".ir", "w", encoding="utf8") as ir_out:
        pprint.pp(module, stream=ir_out)

    module = codegen.translate_wasm(module)
    wasm = codegen.wasm_repr_indented(module)
    with open(output_file, "w", encoding="utf8") as out:
        out.write(wasm)

    return 0


if __name__ == "__main__":
    quit(main(sys.argv[1], sys.argv[2:]))
