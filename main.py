import pprint
import sys


import compiler
import parser
from compiler import codegen


prog = parser.parse_file(sys.argv[1])
if not prog:
    sys.exit(1)


module = compiler.semantic_pass(prog)
pprint.pp(module)


module = codegen.translate_wasm(module)
# pprint.pp(module)
out = open(sys.argv[2], "w")
out.write(codegen.wasm_repr_indented(module))
