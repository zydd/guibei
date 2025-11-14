from parser.combinators import *
from parser.indent import *

from compiler import ast

operator_characters = "-~`!@$%^&*+=|;:',<.>/?"


@generate
def comment():
    yield regex(r"#[^\n]*(\s*#[^\n]*)*")


@generate
def asm():
    @generate
    def wast_term():
        @generate
        def int_literal():
            return int((yield regex(r"-?\d+")))

        term = yield choice(
            regex(r"[a-z]+=\d+"),
            regex(r"[a-z]\w*(\.[a-z]\w*)?"),
            int_literal(),
            regex(r'"[^"]*"'),
            regex(r"[$\w.]+"),
            parens(wast_expr()),
            bracers(expr()),
        )
        return term

    @generate
    def wast_expr():
        return ast.WasmExpr((yield sep_by(indent_spaces(), wast_term())))

    yield string("asm:")
    yield regex(r"\s*")
    yield indented()
    asm = yield with_pos(wast_expr())
    return ast.Asm(asm)


@generate
def typed_id_decl():
    name = yield regex(r"\w+")
    yield regex(r"\s*:\s*")
    type_ = yield type_expr()
    return (name, type_)


@generate
def var_decl():
    yield regex("let +")
    name, type_ = yield typed_id_decl()
    optional_init = yield optional(sequence(regex(r"\s*=\s*"), expr()))
    return ast.VarDecl(name, type_, init=optional_init[1] if optional_init else None)


@generate
def assignment():
    lvalue = yield expr_index()
    yield regex(r"\s*=\s*")
    value = yield expr()
    return ast.Assignment(lvalue, value)


@generate
def function_def():
    @generate
    def fn_ret_type():
        yield regex(r"\s*->\s*")
        return (yield type_expr())

    yield regex("func +")
    name = yield choice(identifier(), operator_identifier())
    yield regex(r" *")
    args = yield parens(sep_by(regex(r"\s*,\s*"), typed_id_decl()))
    args = [ast.ArgDecl(*a) for a in args]
    ret_type = yield optional(fn_ret_type())
    if (yield optional(regex(r" *:"))):
        body = yield indented_block(statement())
    else:
        body = []
    type_ = ast.FunctionType(args, ret_type or ast.VoidType())
    return ast.FunctionDef(name.name, type_, body)


@generate
def function_type():
    @generate
    def fn_ret_type():
        yield regex(r"\s*->\s*")
        return (yield type_expr())

    yield regex("func *")
    args = yield parens(sep_by(regex(r"\s*,\s*"), typed_id_decl()))
    ret_type = yield optional(fn_ret_type())
    return ast.FunctionType(args, ret_type)


@generate
def tuple_def():
    fields = yield parens(sep_by(regex(r"\s*,\s*"), type_expr()))
    return ast.TupleType(fields)


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
    body = yield indented_block(type_expr())
    assert len(body) == 1
    return ast.TypeDef(name, body[-1])


@generate
def native_type():
    yield regex(r"__native_type<")
    args = yield sep_by(regex(r"\s*,\s*"), regex(r"\w+"))
    yield string(">")
    return ast.NativeType(args)


@generate
def int_literal():
    return ast.IntLiteral(int((yield regex(r"-?\d+"))))


@generate
def string_literal():
    value = yield regex(r'"(([^"\\]|\\.)*)"', group=1)
    value = value.encode().decode("unicode_escape")
    return ast.StringLiteral(value)


@generate
def identifier():
    name = yield regex(r"[_a-zA-Z]\w*")
    return ast.Placeholder() if name == "_" else ast.Identifier(name)


@generate
def tuple_expr():
    elements = yield parens(sep_by(regex(r"\s*,\s*"), expr()))
    return ast.TupleExpr(elements)


@generate
def operator_identifier():
    op = yield regex(rf"\([{operator_characters}]+\)")
    return ast.Identifier(op)


@generate
def array_index(array):
    idx = yield brackets(optional(expr()))
    return ast.GetItem(array, idx)


@generate
def attr_access(expr):
    number = generate(lambda: int((yield regex(r"\d+"))))
    yield string(".")
    attr = yield choice(number(), regex(r"\w+"))
    if isinstance(attr, int):
        return ast.GetTupleItem(expr, attr)
    else:
        return ast.GetAttr(expr, attr)


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
    # TODO: BinOp AST node - it should be possible to retrieve the original input from the AST
    for op, rhs in zip(operators, terms):
        res = ast.Call(ast.Identifier(f"({op})"), ast.TupleExpr([res, rhs]))

    return res


@generate
def while_block():
    yield regex("while +")
    condition = yield expr()
    yield regex(r" *:\s*")
    yield indented()
    body = yield with_pos(sep_by(regex(r"\s*"), statement()))
    return ast.While(condition, body)


@generate
def case_block():
    yield regex("case +")
    cond = yield expr()
    yield regex(r" *:\s*")
    body = yield indented_block(statement())
    return ast.MatchCase(cond, body)


@generate
def match_block():
    yield regex("match +")
    cond = yield expr()
    yield regex(r" *:\s*")
    cases = yield indented_block(case_block())
    return ast.Match(cond, cases)


@generate
def if_block():
    @generate
    def else_block():
        yield sequence(regex(r"\s*"), same_indent())
        yield regex(r"else *:\s*")
        return (yield indented_block(statement()))

    yield regex("if +")
    condition = yield expr()
    yield regex(r" *:")
    body_then = yield indented_block(statement())
    body_else = yield optional(else_block())
    return ast.IfElse(condition, body_then, body_else if body_else is not None else [])


@generate
def return_statement():
    yield regex(r"return\b *")
    res = yield optional(expr())
    return ast.FunctionReturn(res if res is not None else ast.VoidExpr())


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
        fields = yield optional(tuple_def())
        return ast.EnumValueType(name, fields)

    yield regex("enum +")
    name = yield regex(r"\w+")
    yield regex(r" *:")
    values = yield indented_block(enum_val())
    return ast.EnumType(name, values)


@generate
def impl():
    yield regex("impl +")
    name = yield regex(r"\w+")
    yield regex(r" *:")
    values = yield indented_block(choice(comment(), function_def()))
    values = [stmt for stmt in values if stmt is not None]
    return ast.TypeImpl(name, values)


@generate
def statement():
    yield optional(sequence(comment(), regex(r"\s*")))
    yield same_indent()
    annotations = yield optional(compiler_annotation())

    yield optional(sequence(comment(), regex(r"\s*")))
    yield same_indent()
    stmt = yield choice(
        while_block(),
        if_block(),
        match_block(),
        return_statement(),
        var_decl(),
        enum_def(),
        impl(),
        type_def(),
        function_def(),
        backtrack(assignment()),
        expr(),
    )
    if annotations:
        stmt.annotations = annotations
    return stmt


@generate
def cast_expr(term):
    yield regex(r" *")
    arg = yield expr_term
    return ast.Call(term, arg)


@generate
def expr_index():
    term = yield expr_term

    while True:
        term_ex = yield optional(choice(attr_access(term), array_index(term), backtrack(cast_expr(term))))
        if not term_ex:
            break
        term = term_ex
    return term


expr_term = choice(function_def(), asm(), int_literal(), string_literal(), identifier(), tuple_expr())

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
def type_name():
    name = yield regex(r"[_a-zA-Z]\w*")
    term = ast.TypeIdentifier(name)

    while True:
        term_ex = yield optional(attr_access(term))
        if not term_ex:
            break
        term = term_ex

    while True:
        term_ex = yield optional(array_type_index(term))
        if not term_ex:
            break
        term = term_ex

    return term


@generate
def array_type_index(array):
    idx = yield brackets(regex(r" *"))
    return ast.ArrayType(array)


@generate
def type_expr():
    term = yield choice(tuple_def(), function_type(), native_type(), type_name())

    while True:
        term_ex = yield optional(attr_access(term))
        if not term_ex:
            break
        term = term_ex
    return term


@generate
def module():
    yield regex(r"\s*")
    res = yield sep_by(regex(r"\s*"), statement())
    yield regex(r"\s*")
    return ast.Module(res)
