from parser.combinators import *
from parser.indent import *

from compiler.fndef import FunctionCall, FunctionDef, VarDecl
from compiler.identifier import Identifier
from compiler.literals import IntLiteral
from compiler.tuple import TupleDef
from compiler.typedef import TypeDef, TypeName
from compiler.wast import Asm, WasmExpr


@generate
def asm():
    def wast_term():
        @generate
        def int_literal():
            return int((yield regex(r"-?\d+")))

        return choice(
            regex(r"[a-z]+=\d+"),
            regex(r"[a-z]\w*(\.[a-z]\w*)?"),
            int_literal(),
            regex(r'"[^"]*"'),
            regex(r"[$\w]+"),
            parens(wast_expr()),
        )

    @generate
    def wast_expr():
        return WasmExpr((yield sep_by(indent_spaces(), wast_term())))

    yield string("asm:")
    yield regex(r"\s*")
    yield indented()
    expr = yield with_pos(wast_expr())
    return Asm(expr)


@generate
def typed_id_decl():
    name = yield regex(r"\w+")
    yield regex(r"\s*:\s*")
    type_ = yield type_expr
    return (name, type_)


@generate
def var_decl():
    yield regex("let +")
    name, type_ = yield typed_id_decl()
    optional_init = yield optional(sequence(regex(r"\s*=\s*"), expr))
    return VarDecl(name, type_, init=optional_init[1] if optional_init else None)


@generate
def function_def():
    @generate
    def fn_ret_type():
        yield regex(r"\s*->\s*")
        return (yield regex(r"\w+"))

    yield regex("func +")
    name = yield regex(r"\w+")
    yield regex(r"\s*")
    args = yield parens(sep_by(regex(r"\s*,\s*"), typed_id_decl()))
    ret_type = yield optional(fn_ret_type())
    yield regex(r"\s*:\s*")
    yield indented()
    body = yield with_pos(sep_by(regex(r"\s*"), statements()))
    return FunctionDef(name, args, ret_type, body)


@generate
def tuple_def():
    fields = yield parens(sep_by(regex(r"\s*,\s*"), type_expr))
    return TupleDef(fields)


# @generate
# def struct_def()
# @generate
# def field_decl():
#     name = yield regex(r"\w+")
#     yield regex(r"\s*:\s*")
#     type_ = yield regex(r"\w+")
#     return (name, type_)
# ...


@generate
def type_def():
    yield regex("type +")
    name = yield regex(r"\w+")
    yield regex(r"\s*:")
    body = yield indented_block(type_expr)
    return TypeDef(name, body)


@generate
def type_name():
    name = yield regex(r"\w+")
    array = yield optional(regex(r"\s*\[\s*\]"))
    return TypeName(name, dimensions=(1,) if array else ())


@generate
def int_literal():
    return IntLiteral(int((yield regex(r"-?\d+"))))


@generate
def identifier():
    return Identifier((yield regex(r"[_a-zA-Z]\w*")))


@generate
def call():
    name = yield regex(r"\w+")
    yield regex(r"\s*")
    args = yield parens(sep_by(regex(r"\s*,\s*"), expr))
    return FunctionCall(name, args)


@generate
def prog():
    return (yield sep_by(regex(r"\s*"), statements()))


type_expr = choice(tuple_def(), type_name())
expr = choice(function_def(), type_def(), asm(), var_decl(), int_literal(), choice(backtrack(call()), identifier()))


@generate
def statements():
    yield same_indent()
    return (yield expr)
