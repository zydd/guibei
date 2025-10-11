from parser.combinators import *
from parser.indent import *

from compiler.call import Call, MethodAccess
from compiler.enum import Enum
from compiler.fndef import FunctionDef, FunctionType, VarDecl
from compiler.identifier import Identifier, operator_characters
from compiler.literals import IntLiteral, StringLiteral
from compiler.statements import Assignment, ReturnStatement, WhileStatement
from compiler.tuple import TupleIndex
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
            bracers(expr()),
        )

    @generate
    def wast_expr():
        return WasmExpr((yield sep_by(indent_spaces(), wast_term())))

    yield string("asm:")
    yield regex(r"\s*")
    yield indented()
    asm = yield with_pos(wast_expr())
    return Asm(asm)


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
    optional_init = yield optional(sequence(regex(r"\s*=\s*"), expr()))
    return VarDecl(name, type_, init=optional_init[1] if optional_init else None)


@generate
def assignment():
    name = yield identifier()
    yield regex(r"\s*=\s*")
    value = yield expr()
    return Assignment(name, value)


@generate
def function_def():
    @generate
    def fn_ret_type():
        yield regex(r"\s*->\s*")
        return (yield type_expr)

    yield regex("func +")
    name = yield choice(identifier(), operator_identifier())
    yield regex(r" *")
    args = yield parens(sep_by(regex(r"\s*,\s*"), typed_id_decl()))
    ret_type = yield optional(fn_ret_type())
    if (yield optional(regex(r" *:"))):
        body = yield indented_block(statement())
    else:
        body = []
    return FunctionDef(str(name), args, ret_type or VoidType(), body)


@generate
def function_type():
    @generate
    def fn_ret_type():
        yield regex(r"\s*->\s*")
        return (yield type_expr)

    yield regex("func *")
    args = yield parens(sep_by(regex(r"\s*,\s*"), typed_id_decl()))
    ret_type = yield optional(fn_ret_type())
    return FunctionType(None, args, ret_type or VoidType())


@generate
def tuple_def():
    fields = yield parens(sep_by(regex(r"\s*,\s*"), type_expr))
    return TupleType(None, fields)


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
    assert len(body) == 1
    return NewType(name, body[-1])


@generate
def native_type():
    type_ = yield regex(r"__native_type<(\w+)>", 1)
    return NativeType(type_)


@generate
def type_identifier():
    name = yield regex(r"[_a-zA-Z0-9]\w*")
    type_ = TypeIdentifier(name)
    array = yield optional(regex(r"\s*\[\s*\]"))
    if array:
        return ArrayType(None, type_)
    else:
        return type_


@generate
def int_literal():
    return IntLiteral(int((yield regex(r"-?\d+"))))


@generate
def string_literal():
    value = yield regex(r'"([^"\\]|\\.)*"')
    return StringLiteral(value)


@generate
def identifier():
    return Identifier((yield regex(r"[_a-zA-Z]\w*")))


@generate
def operator_identifier():
    yield string("(")
    op = yield regex(rf"[{operator_characters}]+")
    yield string(")")
    return Identifier(op)


@generate
def call(callee):
    args = yield parens(sep_by(regex(r"\s*,\s*"), expr()))
    return Call(callee, args)


@generate
def array_index(array):
    idx = yield brackets(expr())
    return ArrayIndex(array, idx)


@generate
def attr_access(expr):
    number = generate(lambda: int((yield regex(r"\d+"))))
    yield string(".")
    attr = yield choice(number(), regex(r"\w+"))
    if isinstance(attr, int):
        return TupleIndex(expr, attr)
    else:
        return MethodAccess(expr, attr)


@generate
def expr_index():
    term = yield expr_term

    while True:
        term_ex = yield optional(choice(call(term), attr_access(term), array_index(term)))
        if not term_ex:
            break
        term = term_ex
    return term


@generate
def binop(ops, unit):
    res = yield unit
    terms = []
    operators = []

    while True:
        op = yield optional(sequence(regex(r"\s*"), ops))
        if op is None:
            break
        op = op[1]
        yield regex(r"\s*")
        rhs = yield unit
        operators.append(op)
        terms.append(rhs)

    # TODO: right-association
    for op, rhs in zip(operators, terms):
        res = Call(Identifier(op), [res, rhs])

    return res


@generate
def while_block():
    yield regex("while +")
    condition = yield expr()
    yield regex(r" *:\s*")
    yield indented()
    body = yield with_pos(sep_by(regex(r"\s*"), statement()))
    return WhileStatement(condition, body)


@generate
def return_statement():
    yield regex("return +")
    return ReturnStatement((yield expr()))


@generate
def compiler_annotation():
    yield string(":[")
    annotations = yield sep_by(regex(r"\s*,\s*"), expr())
    yield string("]\n")
    return annotations


@generate
def enum_def():
    @generate
    def enum_val():
        name = yield regex(r"\w+")
        fields = yield optional(parens(sep_by(regex(r"\s*,\s*"), type_expr)))
        return name, fields

    yield regex("enum +")
    name = yield regex(r"\w+")
    yield regex(r" *:")
    values = yield indented_block(enum_val())
    return Enum(name, values)


@generate
def impl():
    yield regex("impl +")
    name = yield regex(r"\w+")
    yield regex(r" *:")
    values = yield indented_block(function_def())
    return TypeImpl(name, values)


@generate
def statement():
    yield same_indent()
    annotations = yield optional(compiler_annotation())

    yield same_indent()
    stmt = yield choice(
        while_block(),
        return_statement(),
        var_decl(),
        enum_def(),
        impl(),
        backtrack(assignment()),
        expr(),
    )
    if annotations:
        stmt.annotations = annotations
    return stmt


type_expr = choice(tuple_def(), function_type(), native_type(), type_identifier())
expr_term = choice(function_def(), type_def(), asm(), int_literal(), string_literal(), identifier())

operators = [
    regex(r"\*|/|%"),
    regex(r"\+|-"),
    regex(r"<=|>=|>|<"),
    regex(r"==|!="),
    regex(r"&"),
    regex(r"\|"),
]

op_parser = expr_index()
for op in operators:
    op_parser = binop(op, op_parser)


def expr():
    return op_parser


@generate
def prog():
    yield regex(r"\s*")
    res = yield sep_by(regex(r"\s*"), statement())
    yield regex(r"\s*")
    yield eof()
    return res
