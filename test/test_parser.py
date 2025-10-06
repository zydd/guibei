import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser
from parser.lang import *


@pytest.mark.parametrize("code", [
    "call().0",
    "call()[0]",
    "call[0].0",
    "call[0]()",
    "call[0]().0",
])
def test_expr_index(code):
    assert parser.run_parser(expr_index(), code)


@pytest.mark.parametrize("code", [
    "type test:\n    (i32, i32)",
    "type test: (i32, i32, i32)",
    "type int:\n    i32",
    "type test:\n    i322",
])
def test_type_def(code):
    assert parser.run_parser(type_def(), code)


@pytest.mark.parametrize("code", [
    "i32",
    "i32[]",
])
def test_type_identifier(code):
    assert parser.run_parser(type_identifier(), code)


@pytest.mark.parametrize("code", [
    "quit()",
    "quit( )",
    "readn(0, 1024)",
    "printn(0, read_count)",
])
def test_expr(code):
    assert parser.run_parser(expr(), code)


@pytest.mark.parametrize("code", [
    "1+2",
    "1+2+3",
    "1+2-3",
    "1-2+3",
    "1*2*3",
    "1|2|3",
    "1*2+3",
    "1+2*3",
    "1+2*3 | 4+5*6",
])
def test_op_parser(code):
    assert parser.run_parser(op_parser, code)
