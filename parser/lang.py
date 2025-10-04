from parser.combinators import *
from parser.indent import *

from compiler.call import Call
from compiler.fndef import FunctionDef, VarDecl
from compiler.identifier import Identifier
from compiler.literals import IntLiteral
from compiler.tuple import TupleDecl, TupleIndex
from compiler.typedef import *
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
        return (yield type_expr)

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
    return TupleDecl(fields)


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
def native_type():
    type_ = yield regex(r"__native_type<(\w+)>", 1)
    return NativeType(type_)


@generate
def type_name():
    name = yield regex(r"[_a-zA-Z]\w*")
    array = yield optional(regex(r"\s*\[\s*\]"))
    if array:
        return ArrayType(name, dimensions=(1,))
    else:
        return TypeName(name)


@generate
def int_literal():
    return IntLiteral(int((yield regex(r"-?\d+"))))


@generate
def identifier():
    return Identifier((yield regex(r"[_a-zA-Z]\w*")))


@generate
def call():
    name = yield regex(r"[_a-zA-Z]\w*")
    yield regex(r"\s*")
    args = yield parens(sep_by(regex(r"\s*,\s*"), expr))
    return Call(name, args)


@generate
def tuple_index():
    var = yield identifier()
    yield string(".")
    idx = int((yield regex(r"\d+")))
    return TupleIndex(var, idx)


@generate
def statements():
    yield same_indent()
    return (yield expr)


type_expr = choice(tuple_def(), native_type(), type_name())
expr = choice(function_def(), type_def(), asm(), var_decl(), int_literal(), choice(backtrack(call()), backtrack(tuple_index()), identifier()))
prog = sep_by(regex(r"\s*"), statements())
