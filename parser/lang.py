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
            return int((yield regex(r"-?(0x)?\d+")))

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
    name = yield _name()
    type_ = yield optional(sequence(regex(r"\s*:\s*"), type_expr(), index=1))
    return (name, type_)


@generate
def var_decl():
    yield regex("let +")
    name, type_ = yield _typed_id_decl()
    optional_init = yield optional(sequence(regex(r"\s*=\s*"), expr()))
    return ast.VarDecl(name, type_, init=optional_init[1] if optional_init else None)


@generate
def const_decl():
    yield regex("const +")
    name, type_ = yield _typed_id_decl()
    init = yield sequence(regex(r"\s*=\s*"), expr(), index=1)
    return ast.ConstDecl(name, type_, init)


@generate
def assignment():
    lvalue = yield expr()
    yield regex(r"\s*=\s*")
    value = yield expr()
    return ast.Assignment(lvalue, value)


@generate
def macro_def():
    yield regex("macro +")
    ast_macro = yield optional(string(":"))
    name = yield choice(identifier(), operator_identifier())
    yield regex(r" *")
    args = yield _function_args()
    ret_type = yield (optional(_function_ret()))
    yield regex(r" *:")
    body = yield indented_block(statement())

    func = ast.FunctionDef(name.name, ast.FunctionType(args, ret_type), body)

    if ast_macro:
        return ast.AstMacroDef(name.name, func)
    else:
        return ast.MacroDef(name.name, func)


@generate
def ast_macro_inst():
    yield regex(":")
    macro = yield identifier()
    arg = yield tuple_expr()
    return ast.AstMacroInst(macro.name, arg)


@generate
def function_def():
    yield regex("func +")
    name = yield choice(identifier(), operator_identifier())
    yield regex(r" *")
    args, ret_type = yield sequence(_function_args(), _function_ret())
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
    fields = yield parens(sep_by(regex(r"\s*,\s*"), choice(backtrack(named_tuple_element(type_expr())), type_expr())))
    return ast.TupleType(fields)


# @generate
# def struct_def()
# @generate
# def field_decl():
#     name = yield _name()
#     yield regex(r"\s*:\s*")
#     type_ = yield _name()
#     return (name, type_)
# ...


@generate
def type_def():
    yield regex("type +")
    name = yield _name()
    args = yield optional(brackets(sep_by(regex(r"\s*,\s*"), identifier(), min_count=1)))
    body = yield optional(sequence(regex(r"\s*:\s*"), indented_block(type_expr()), index=1))

    if args:
        return ast.TemplateDef(name, args, body[-1] if body else None)
    else:
        return ast.TypeDef(name, body[-1] if body else None)


@generate
def int_literal():
    val = yield regex(r"0x[a-fA-F0-9]+|\d+")
    if val.startswith("0x"):
        val = int(val, 16)
    else:
        val = int(val)
    return ast.IntLiteral(val)


@generate
def _escaped_text(quote):
    text = yield regex(rf"{quote}(([^{quote}\\]|\\.)*){quote}", group=1)
    return text.encode().decode("unicode_escape")


@generate
def string_literal():
    text = yield _escaped_text('"')
    return ast.StringLiteral(text)


# @generate
# def char_literal():
#     text = yield _escaped_text("'")
#     return ast.CharLiteral(text)


def _name():
    return regex(r"(?!(asm|if|func|while|macro|const|impl|in)\b)[_a-zA-Z]\w*")


@generate
def identifier():
    name = yield _name()
    return ast.Placeholder() if name == "_" else ast.Identifier(name)


@generate
def named_tuple_element(p):
    name = yield _name()
    yield regex(r"\s*:\s*")
    value = yield p
    return ast.NamedTupleElement(name, value)


@generate
def tuple_expr():
    elements = yield parens(sep_by(regex(r"\s*,\s*"), choice(backtrack(named_tuple_element(expr())), expr())))
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
    yield string(".")
    attr = yield choice(regex(r"\d"), _name())
    return ast.GetAttr(expr, attr)


def unaryop(unop):
    @generate
    def _unaryop(unit):
        ops = yield many(unop)
        term = yield unit
        for op in reversed(ops):
            term = ast.UnaryL(op, term)
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
        for op, rhs in zip(operators, terms):
            res = ast.BinOp(op, res, rhs)

        return res

    return _binop


@generate
def ast_for_block():
    yield regex(":for +")
    bindings = yield sep_by(regex(r"\s*,\s*"), identifier())
    yield regex(r" +in +")
    iterable = yield expr()
    yield regex(r" *:\s*")
    body = yield indented_block(statement())
    return ast.TemplateFor(bindings, iterable, body)


@generate
def while_block():
    yield regex("while +")
    condition = yield expr()
    yield regex(r" *:\s*")
    yield indented()
    body = yield indented_block(statement())
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
        name = yield _name()
        fields = yield optional(tuple_def())
        return ast.EnumValueType(name, fields)

    yield regex("enum +")
    name = yield _name()
    yield regex(r" *:")
    values = yield indented_block(enum_val())
    return ast.EnumType(name, values)


@generate
def impl():
    yield string("impl")
    args = yield optional(brackets(sep_by(regex(r"\s*,\s*"), type_expr(), min_count=1)))
    yield regex(" +")
    name = yield type_name()
    yield regex(r" *:")
    methods = yield indented_block(choice(comment(), function_def(), macro_def(), ast_macro_inst()))
    methods = [stmt for stmt in methods if stmt is not None]
    if args:
        return ast.TemplateTypeImpl(args, name, methods)
    else:
        return ast.TypeImpl(name, methods)


@generate
def statement():
    yield optional(sequence(comment(), regex(r"\s*")))
    yield same_indent()
    annotations = yield optional(compiler_annotation())

    yield optional(sequence(comment(), regex(r"\s*")))
    yield same_indent()
    stmt = yield choice(
        ast_for_block(),
        while_block(),
        if_block(),
        match_block(),
        return_statement(),
        var_decl(),
        const_decl(),
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
    binop(regex(r"&(?!&)")),
    binop(regex(r"\|(?!\|)")),
    binop(regex(r"<=|>=|>|<|==|!=")),
    binop(regex(r"&&")),
    binop(regex(r"\|\|")),
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
        term_ex = yield optional(choice(attr_access(term), template_args(term)))
        if not term_ex:
            break
        term = term_ex

    return term


@generate
def array_type():
    type_ = yield brackets(type_expr())
    return ast.ArrayType(type_)


@generate
def native_array():
    yield string("__native_array")
    type_ = yield brackets(type_expr())
    return ast.NativeArrayType(type_)


@generate
def template_args(term):
    args = yield brackets(sep_by(regex(r"\s*,\s*"), type_expr(), min_count=1))
    return ast.TemplateInst(term, args)


@generate
def integral_type():
    yield string("__integral")
    args = yield brackets(sep_by(regex(r"\s*,\s*"), regex(r"[\w.]+")))
    return ast.IntegralType(*args)


@generate
def type_expr():
    term = yield choice(integral_type(), tuple_def(), function_type(), array_type(), type_name())
    return term


@generate
def module():
    yield regex(r"\s*")
    res = yield sep_by(regex(r"\s*"), statement())
    yield regex(r"\s*")
    return ast.Module(res)
