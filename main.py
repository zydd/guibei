import pprint
import sys


import compiler
import parser


prog = parser.parse_file(sys.argv[1])
if not prog:
    sys.exit(1)


module = compiler.semantic_pass(prog)
pprint.pp(module)

quit()
compiler = compiler.CompilePass()
compiler.compile(prog)
compiler.write(open(sys.argv[2], "wb"))
