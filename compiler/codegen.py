from . import ir
from . import traverse_ir


def wasm_repr_indented(expr: list[str | int | list], level=0) -> str:
    indent = "    " * level
    if len(expr) == 1 and not isinstance(expr[0], list):
        return f"{indent}({expr[0]})"
    else:
        terms = []
        if expr:
            terms.append("\n" + wasm_repr_indented(expr[0], level + 1) if isinstance(expr[0], list) else str(expr[0]))
            n = 1
            if len(expr) > 1 and expr[0] != "elem" and isinstance(expr[1], str) and expr[1].startswith("$"):
                terms[0] += " " + expr[1]
                n += 1
            for term in expr[n:]:
                terms.append(
                    wasm_repr_indented(term, level + 1) if isinstance(term, list) else f"{'    ' * (level + 1)}{term}"
                )
        inner = "\n".join(terms)
        if len(inner) < 80:
            return indent + _wasm_repr_flat(expr)
        return f"{indent}({inner}\n{indent})"


def _wasm_repr_flat(expr):
    format = lambda term: _wasm_repr_flat(term) if isinstance(term, list) else str(term)
    return f"({' '.join(map(format, expr))})"


def type_reference(node: ir.Node) -> list:
    match node:
        case ir.NativeType():
            return [node.name]

        case ir.TypeDef():
            primitive = node.primitive()
            if isinstance(primitive, ir.NativeType):
                return type_reference(primitive)
            return [["ref", f"${node.name}"]]

        case ir.TypeRef():
            return type_reference(node.type_)

        # case ir.VoidType():
        #     return []

    raise NotImplementedError(type(node))


def type_declaration(node: ir.Node) -> list:
    match node:
        case ir.NativeType():
            return [node.name]

        case ir.EnumType():
            return [["type", f"${node.name}", "(sub $__enum (struct (field (ref i31))))"]]

        case ir.EnumValueType():
            fields = [["field", *type_reference(type_)] for type_ in node.field_types]
            assert isinstance(node.super_, ir.TypeRef)
            return [
                [
                    "type",
                    f"${node.name}",
                    ["sub", f"${node.super_.name}", ["struct", "(field (ref i31))", *fields]],
                ],
            ]

        case ir.TypeDef():
            primitive = node.primitive()
            if isinstance(primitive, ir.NativeType):
                return []
            decl = type_declaration(primitive)

            if isinstance(node.super_, ir.TypeRef) and isinstance(node.super_.primitive(), ir.TupleType):
                decl = [["sub", f"${node.super_.name}", *decl]]

            return [["type", f"${node.name}", *decl]]

        case ir.ArrayType():
            element_primitive = node.element_type.primitive()
            if isinstance(element_primitive, ir.NativeType) and element_primitive.array_packed:
                return [["array", ["mut", element_primitive.array_packed]]]
            else:
                return [["array", ["mut", *type_declaration(element_primitive)]]]

        case ir.TypeRef() | ir.FunctionDef():
            return []

    raise NotImplementedError(type(node))


def translate_wasm(node: ir.Node) -> list[str | int | list]:
    match node:
        case ir.Module():
            terms: list = ["module"]
            for expr in node.asm:
                terms.extend(translate_wasm(expr))

            for attr in node.scope.attrs.values():
                terms.extend(type_declaration(attr))

            for attr in node.scope.attrs.values():
                terms.extend(translate_wasm(attr))

            return terms

        case ir.IntLiteral():
            return [f"(i32.const {node.value})"]

        case ir.VoidType():
            return []

        case ir.WasmExpr():
            return [translate_wasm(term) if isinstance(term, ir.Node) else term for term in node.terms]

        case ir.TypeDef():
            return translate_wasm(node.scope)

        case ir.TypeRef():
            return []

        case ir.FunctionDef():
            decls: list = [["param", f"${arg.name}", *type_reference(arg.type_)] for arg in node.type_.args]
            if not isinstance(node.type_.ret_type, ir.VoidType):
                decls.append(["result", *type_reference(node.type_.ret_type)])

            body = translate_wasm(node.scope)

            return [
                ["type", f"${node.name}.__type", ["func", *decls]],
                ["func", f"${node.name}", ["type", f"${node.name}.__type"], *body],
            ]

        case ir.FunctionReturn():
            return [["return", *translate_wasm(node.expr)]]

        case ir.Scope():
            terms = []
            for expr in node.attrs.values():
                match expr:
                    case ir.VarDecl() | ir.FunctionDef():
                        terms.extend(translate_wasm(expr))

                    # TODO
                    case ir.TypeRef() | ir.VarRef() | ir.OverloadedFunction():
                        pass
                    case _:
                        raise NotImplementedError(type(expr))
            for expr in node.body:
                terms.extend(translate_wasm(expr))
            return terms

        case ir.VarDecl():
            return [["local", f"${node.name}"]]

        case ir.VarRef():
            return [["local.get", f"${node.var.name}"]]

        case ir.Asm():
            assert isinstance(node.terms, ir.WasmExpr)
            terms = []
            for term in node.terms.terms:
                if isinstance(term, ir.Node):
                    terms.append(translate_wasm(term))
                else:
                    terms.append(term)
            return terms

        case ir.SetLocal():
            return [["local.set", f"${node.var.var.name}", *translate_wasm(node.expr)]]

        case ir.IfElse():
            else_block = [["else", *translate_wasm(node.scope_else)]] if node.scope_else.body else []
            return [["if", *translate_wasm(node.condition), ["then", *translate_wasm(node.scope_then)], *else_block]]

        case ir.Loop():
            body = translate_wasm(node.scope)
            assert node.post_condition is None
            id = 0
            return [
                [
                    "block",
                    f"${node.scope.name}.__block",
                    [
                        "loop",
                        f"${node.scope.name}.__loop",
                        [
                            "br_if",
                            f"${node.scope.name}.__block",
                            ["i32.eqz", *translate_wasm(node.pre_condition)],
                        ],
                        *body,
                        ["br", f"$while_loop_{id}"],
                    ],
                ]
            ]

        # TODO
        case ir.Assignment(lvalue=ir.VarRef()):
            assert isinstance(node.lvalue, ir.VarRef)
            return [["local.set", f"${node.lvalue.var.name}", *translate_wasm(node.expr)]]

        case ir.Call(callee=ir.FunctionRef()):
            return [
                ["call", f"${node.callee.function.name}"] + [term for arg in node.args for term in translate_wasm(arg)]
            ]

        # case _:
        #     print(type(node))
        #     return traverse_ir.traverse(translate_wasm, node)

    return [str(node)]
    raise NotImplementedError(node)
