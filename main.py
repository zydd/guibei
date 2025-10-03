import parser

import compiler as compiler
import sys


prog = parser.parse_file(sys.argv[1])
if not prog:
    sys.exit(1)

compiler = compiler.CompilePass()
compiler.compile(prog)
compiler.write(open(sys.argv[2], "wb"))
