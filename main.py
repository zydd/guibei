import pprint
import sys


import compiler
import parser
from compiler import codegen


files_content = ""
for filename in sys.argv[2:]:
    with open(filename, "r", encoding="utf8") as f:
        files_content += f.read() + "\n"

prog = parser.parse_str(files_content)
if not prog:
    sys.exit(1)


module = compiler.semantic_pass(prog)
pprint.pp(module)


module = codegen.translate_wasm(module)
# pprint.pp(module)
out = open(sys.argv[1], "w")
out.write(codegen.wasm_repr_indented(module))
