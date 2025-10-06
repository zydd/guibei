import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser
from parser.lang import *


def test_parser(p, examples, print_result=False):
    print("Parser:", p.__name__)
    for ex in examples.split("\0"):
        if not ex:
            continue
        print(repr(ex))
        res = parser.run_parser(p, ex)
        if print_result:
            print(str(res))
        assert res
    print()


test_parser(expr_index(), """\
quit().0\0\
""")



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


test_parser(type_identifier(), """\
i32\0\
i32[]\0\
""")


test_parser(expr(), """\
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


test_parser(op_parser, """\
1+2\0\
1+2+3\0\
1+2-3\0\
1-2+3\0\
1*2*3\0\
1|2|3\0\
1*2+3\0\
1+2*3\0\
1+2*3 | 4+5*6\0\
""", print_result=True)