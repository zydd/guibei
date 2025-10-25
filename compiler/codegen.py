from . import ir


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
