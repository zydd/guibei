import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser
from parser.lang import *


@pytest.mark.parametrize(
    "code",
    [
        "call().0",
        "call()[0]",
        "call[0].0",
        "call[0]()",
        "call[0]().0",
    ],
)
def test_expr_index(code):
    assert parser.run_parser(expr_index(), code)


@pytest.mark.parametrize(
    "code",
    [
        "type test:\n    (i32, i32)",
        "type test: (i32, i32, i32)",
        "type int:\n    i32",
        "type test:\n    i322",
    ],
)
def test_type_def(code):
    assert parser.run_parser(type_def(), code)


@pytest.mark.parametrize(
    "code",
    [
        "i32",
        "i32[]",
    ],
)
def test_type_identifier(code):
    assert parser.run_parser(type_identifier(), code)


# expr


@pytest.mark.parametrize(
    "code",
    [
        "quit()",
        "quit( )",
        "readn(0, 1024)",
        "printn(0, read_count)",
        "2 + 2",
        "a + b",
        "a() + b.1",
    ],
)
def test_expr(code):
    assert parser.run_parser(expr(), code)


@pytest.mark.parametrize(
    "code",
    [
        "",
        "\n",
        " 2",
        "2 ",
    ],
)
def test_expr_fail(code):
    with pytest.raises(ValueError):
        parser.run_parser(expr(), code)


# op_parser


@pytest.mark.parametrize(
    "code",
    [
        "1+2",
        "1+2+3",
        "1+2-3",
        "1-2+3",
        "1*2*3",
        "1|2|3",
        "1*2+3",
        "1+2*3",
        "1+2*3 | 4+5*6",
    ],
)
def test_op_parser(code):
    assert parser.run_parser(op_parser, code)


# sep_py


@pytest.mark.parametrize(
    "sep, p, code",
    [
        (string("-"), string("x"), ""),
        (string("-"), string("x"), "x"),
        (string("-"), string("x"), "x-x-x"),
    ],
)
def test_sep_by(sep, p, code):
    ps = sep_by(sep, p)
    parser.run_parser(ps, code)


@pytest.mark.parametrize(
    "sep, p, code",
    [
        (string("-"), string("x"), "-"),
        (string("-"), string("x"), "x-"),
        (string("-"), string("x"), "-x"),
    ],
)
def test_sep_by_fail(sep, p, code):
    ps = sep_by(sep, p)
    with pytest.raises(ValueError):
        parser.run_parser(ps, code)


# indented_block


@pytest.mark.parametrize(
    "p, code",
    [
        (string("x"), " x"),
        (string("x"), " x\n x"),
        (string("x"), " x\n x\n x"),
        (string("x"), " x\n x"),
    ],
)
def test_indented_block(p, code):
    block = indented_block(p)
    parser.run_parser(block, code)


@pytest.mark.parametrize(
    "p, code",
    [
        (string("x"), ""),
        (string("x"), " "),
        (string("x"), "\n"),
        (string("x"), "x"),
        (string("x"), "x\nx\n"),
        (string("x"), " x\n"),
    ],
)
def test_indented_block_fail(p, code):
    block = indented_block(p)
    with pytest.raises(Exception):
        parser.run_parser(block, code)


# function_def


@pytest.mark.parametrize(
    "code",
    [
        "func fn1() -> i32:\n return 0",
        "func fn1() -> i32:\n return 0\n return 1",
    ],
)
def test_func_def(code):
    assert parser.run_parser(function_def(), code)


@pytest.mark.parametrize(
    "code",
    [
        "func fn1() -> i32:\n  0\n",  # Should not consume tailing spaces
    ],
)
def test_func_def_fail(code):
    with pytest.raises(ValueError):
        parser.run_parser(function_def(), code)


# impl


@pytest.mark.parametrize(
    "code",
    [
        "impl Type: func fn() -> i32: 0",
        "impl Type:\n func fn() -> i32:\n  0",
        "impl Type:\n func fn1() -> i32:\n  0\n func fn2() -> i32:\n  0",
    ],
)
def test_impl_parser(code):
    assert parser.run_parser(impl(), code)
