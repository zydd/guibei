from . import ir
from . import traverse_ir


def wasm_repr_indented(expr: ir.WasmExpr | ir.Asm, level=0) -> str:
    if isinstance(expr, ir.Asm):
        assert isinstance(expr.terms, ir.WasmExpr)
        return "\n".join(wasm_repr_indented(term, level) for term in expr.terms.terms)  # type: ignore[arg-type]

    indent = "    " * level
    if len(expr.terms) == 1 and not isinstance(expr.terms[0], ir.Node):
        return f"{indent}({expr.terms[0]})"
    else:
        terms = []
        if expr.terms:
            terms.append(
                "\n" + wasm_repr_indented(expr.terms[0], level + 1)
                if isinstance(expr.terms[0], ir.Node)
                else str(expr.terms[0])
            )
            n = 1
            if (
                len(expr.terms) > 1
                and expr.terms[0] != "elem"
                and isinstance(expr.terms[1], str)
                and expr.terms[1].startswith("$")
            ):
                terms[0] += " " + expr.terms[1]
                n += 1
            for term in expr.terms[n:]:
                terms.append(
                    wasm_repr_indented(term, level + 1)
                    if isinstance(term, ir.Node)
                    else f"{'    ' * (level + 1)}{term}"
                )
        inner = "\n".join(terms)
        if len(inner) < 100:
            return indent + _wasm_repr_flat(expr)
        return f"{indent}({inner}\n{indent})"


def _wasm_repr_flat(expr):
    format = lambda term: _wasm_repr_flat(term) if isinstance(term, ir.WasmExpr) else str(term)
    return f"({' '.join(map(format, expr.terms))})"


def type_reference(node: ir.Node) -> list:
    match node:
        case ir.NativeType():
            return [node.name]

        case ir.TypeDef():
            primitive = node.primitive()
            if isinstance(primitive, ir.NativeType):
                return type_reference(primitive)
            return [ir.WasmExpr(None, ["ref", f"${node.name}"])]

        case ir.TypeRef():
            return type_reference(node.type_)

    raise NotImplementedError(type(node))


def type_declaration(node: ir.Node) -> list:
    match node:
        case ir.NativeType():
            return [node.name]

        case ir.EnumType():
            decls = [ir.WasmExpr(node.ast_node, ["type", f"${node.name}", "(sub $__enum (struct (field (ref i31))))"])]
            return decls

        case ir.EnumValueType():
            fields = [["field", *type_reference(type_)] for type_ in node.field_types]
            assert isinstance(node.super_, ir.TypeRef)
            return [
                ir.WasmExpr(
                    None,
                    [
                        "type",
                        f"${node.name}",
                        ["sub", f"${node.super_.name}", ["struct", "(field (ref i31))", *fields]],
                    ],
                )
            ]

        case ir.TypeDef():
            primitive = node.primitive()
            if isinstance(primitive, ir.NativeType):
                return []
            decl = type_declaration(primitive)

            if isinstance(node.super_, ir.TypeRef) and isinstance(node.super_.primitive(), ir.TupleType):
                decl = [["sub", f"${node.super_.name}", *decl]]

            return [ir.WasmExpr(None, ["type", f"${node.name}", *decl])]

        case ir.ArrayType():
            element_primitive = node.element_type.primitive()
            if isinstance(element_primitive, ir.NativeType) and element_primitive.array_packed:
                return [ir.WasmExpr(node.ast_node, ["array", ["mut", element_primitive.array_packed]])]
            else:
                return [ir.WasmExpr(node.ast_node, ["array", ["mut", *type_declaration(element_primitive)]])]

        case ir.TypeRef():
            return []

    raise NotImplementedError(type(node))


def translate_wasm(node: ir.Node, terms=None) -> ir.WasmExpr:
    match node:
        case ir.Module():
            terms = ["module"]
            asm_wasm = [translate_wasm(asm) for asm in node.asm]
            for expr in asm_wasm:
                if isinstance(expr, ir.WasmExpr):
                    terms.extend(expr.terms)
                else:
                    terms.append(expr)

            for type_ in node.scope.attrs.values():
                if not isinstance(type_, ir.Type):
                    continue
                terms.extend(type_declaration(type_))

            return ir.WasmExpr(node.ast_node, terms)

        # case ir.Asm():
        #     assert isinstance(node.terms, ir.WasmExpr)
        #     node.terms = translate_wasm(node.terms)
        #     return node

        case ir.WasmExpr():
            node.terms = [translate_wasm(term) if isinstance(term, ir.Node) else term for term in node.terms]
            return node

        case _:
            return traverse_ir.traverse(translate_wasm, node)

    raise NotImplementedError(node)
