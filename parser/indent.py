from parser.combinators import *


def with_pos(p):
    def parser(input):
        indent = input.indent
        input.indent = input.column
        result, input = p(input)
        input.indent = indent
        return result, input

    return parser


def same_indent():
    def parser(input):
        if input.column != input.indent:
            raise ValueError(input.context() + f"\nExpected indent == {input.indent}, found {input.column}")
        return None, input

    return parser


def indented():
    def parser(input):
        if input.column <= input.indent:
            raise ValueError(input.context() + f"\nExpected indent > {input.indent}, found {input.column}")
        return None, input

    return parser


@generate
def indented_block(p):
    @generate
    def next_line():
        yield regex(r"\s*\n\s*")
        yield same_indent()

    yield regex(r"\s*")
    yield indented()
    body = yield with_pos(sep_by(next_line(), p, min_count=1))
    return body


def indent_spaces():
    compiled = re.compile(r"\s*")

    def parser(input):
        res = ""
        match = compiled.match(input.current())
        if match:
            res = match.group(0)
            input = input.advance(len(match.group(0)))

        if input.column < input.indent:
            raise ValueError(input.context() + f"\nUnexpected indent level")

        return res, input

    return parser


@generate
def parens(p):
    yield regex(r"\(\s*")
    res = yield with_pos(p)
    yield regex(r"\s*\)")
    return res
