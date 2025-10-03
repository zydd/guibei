import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser
from parser.lang import *


test_type_def = """\
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
"""

for code in test_type_def.split("\0"):
    if not code:
        continue
    print(repr(code))
    prog = parser.run_parser(type_def(), code)
    assert prog


test_type_name = """\
i32\0\
i32[]\0\
"""

for code in test_type_name.split("\0"):
    if not code:
        continue
    print(repr(code))
    prog = parser.run_parser(type_name(), code)
    assert prog


test_call = """\
quit()\0\
quit( )\0\
readn(0, 1024)\0\
\0\
printn(0, read_count)\0\
\0\
"""

for code in test_call.split("\0"):
    if not code:
        continue
    print(repr(code))
    prog = parser.run_parser(call(), code)
    assert prog
