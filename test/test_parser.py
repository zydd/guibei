import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser
from parser.lang import *


def test_parser(p, examples):
    print("Parser:", p.__name__)
    for ex in examples.split("\0"):
        if not ex:
            continue
        print(repr(ex))
        prog = parser.run_parser(p, ex)
        assert prog
    print()


test_parser(type_def(), """\
type test:
    (i32, i32)\0\
\0\
type test: (i32, i32, i32)\0\
\0\
type int:
    i32\0\
\0\
type test:
    i322\0\
\0\
""")


test_parser(type_name(), """\
i32\0\
i32[]\0\
""")


test_parser(call(), """\
quit()\0\
quit( )\0\
readn(0, 1024)\0\
printn(0, read_count)\0\
""")

test_parser(expr(), """\
quit()\0\
quit( )\0\
readn(0, 1024)\0\
printn(0, read_count)\0\
""")
