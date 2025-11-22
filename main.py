import pprint
import sys


import compiler
import parser
from compiler import codegen


def main(output_file, input_files):
    code = ""
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
    out = open(output_file, "w")
    out.write(codegen.wasm_repr_indented(module))

    return 0


if __name__ == "__main__":
    quit(main(sys.argv[1], sys.argv[2:]))
