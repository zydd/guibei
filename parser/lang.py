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
def _typed_id_decl():
    name = yield regex(r"\w+")
    yield regex(r"\s*:\s*")
    type_ = yield type_expr()
    return (name, type_)


@generate
def var_decl():
    yield regex("let +")
    name, type_ = yield _typed_id_decl()
    optional_init = yield optional(sequence(regex(r"\s*=\s*"), expr()))
    return ast.VarDecl(name, type_, init=optional_init[1] if optional_init else None)


@generate
def assignment():
    lvalue = yield expr()
    yield regex(r"\s*=\s*")
    value = yield expr()
    return ast.Assignment(lvalue, value)


@generate
def macro_def():
    yield regex("macro +")
    name = yield choice(identifier(), operator_identifier())
    yield regex(r" *")
    args = yield _function_args()
    ret_type = yield (optional(_function_ret()))
    yield regex(r" *:")
    body = yield indented_block(statement())

    func = ast.FunctionDef(name.name, ast.FunctionType(args, ret_type), body)
    return ast.MacroDef(name.name, func)


@generate
def function_def():
    yield regex("func +")
    name = yield choice(identifier(), operator_identifier())
    yield regex(r" *")
    args, ret_type = yield (sequence(_function_args(), _function_ret()))
    if (yield optional(regex(r" *:"))):
        body = yield indented_block(statement())
    else:
        body = []
    type_ = ast.FunctionType(args, ret_type)
    return ast.FunctionDef(name.name, type_, body)


def _function_ret():
    return sequence(regex(r" *-> *"), type_expr(), index=1)


@generate
def _function_args():
    args = yield parens(sep_by(regex(r"\s*,\s*"), _typed_id_decl()))
    return [ast.ArgDecl(*a) for a in args]


@generate
def function_type():
    yield regex("func *")
    args = yield _function_args()
    ret_type = yield optional(_function_ret())
    return ast.FunctionType(args, ret_type)


@generate
def tuple_def():
    fields = yield parens(sep_by(regex(r"\s*,\s*"), choice(backtrack(named_tuple_element()), type_expr())))
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
    body = yield optional(sequence(regex(r"\s*:"), indented_block(type_expr()), index=1))
    return ast.TypeDef(name, body[-1] if body else None)


@generate
def native_type():
    yield regex(r"__native_type<")
    args = yield sep_by(regex(r"\s*,\s*"), regex(r"\w+"))
    yield string(">")
    return ast.NativeType(args)


@generate
def int_literal():
    return ast.IntLiteral(int((yield regex(r"\d+"))))


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
def named_tuple_element():
    name = yield regex(r"\w+")
    yield regex(r"\s*:\s*")
    value = yield expr()
    return ast.NamedTupleElement(name, value)


@generate
def tuple_expr():
    elements = yield parens(sep_by(regex(r"\s*,\s*"), choice(backtrack(named_tuple_element()), expr())))
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
def call(unit, callee):
    arg = yield unit
    return ast.Call(callee, arg)


@generate
def attr_access(expr):
    number = generate(lambda: int((yield regex(r"\d+"))))
    yield string(".")
    attr = yield choice(number(), regex(r"\w+"))
    if isinstance(attr, int):
        return ast.GetTupleItem(expr, attr)
    else:
        return ast.GetAttr(expr, attr)


def unaryop(unop):
    @generate
    def _unaryop(unit):
        ops = yield many(unop)
        term = yield unit
        for op in reversed(ops):
            term = ast.Call(ast.Identifier(f"unary({op})"), term)
        return term

    return _unaryop


def binop(binop):
    @generate
    def _binop(unit):
        res = yield unit
        terms = []
        operators = []

        while True:
            op = yield optional(sequence(regex(r"\s*"), binop))
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

    return _binop


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
    return ast.FunctionReturn(res)


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
    values = yield indented_block(choice(comment(), function_def(), macro_def()))
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
        macro_def(),
        backtrack(assignment()),
        expr(),
    )
    if annotations:
        stmt.annotations = annotations
    return stmt


@generate
def expr_index(unit):
    term = yield unit
    while True:
        term_ex = yield optional(choice(attr_access(term), array_index(term), call(unit, term)))
        if not term_ex:
            break
        term = term_ex
    return term


@generate
def cast_expr(unit):
    callee = yield unit
    while True:
        arg = yield optional(sequence(regex(r" +"), not_followed_by(regex(rf"[{operator_characters}]")), unit, index=2))
        if not arg:
            break
        # TODO: ast.Cast
        callee = ast.Call(callee, arg)
    return callee


expr_term = choice(function_def(), asm(), int_literal(), string_literal(), identifier(), tuple_expr())


precedence = [
    expr_index,
    cast_expr,
    unaryop(regex(r"\+|-")),
    binop(regex(r"\*|//|/|%")),
    binop(regex(r"\+|-")),
    binop(regex(r"&")),
    binop(regex(r"\&")),
    binop(regex(r"\|")),
    binop(regex(r"<=|>=|>|<|==|!=")),
]
for op in precedence:
    expr_term = op(expr_term)


def expr():
    return expr_term


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
