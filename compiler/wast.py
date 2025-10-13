from parser.combinators import *
from parser.indent import *
from compiler.ast import AstNode


class WasmExpr(AstNode):
    def __init__(self, terms):
        self.terms = [WasmExpr(t) if isinstance(t, list) else t for t in terms]

    def __repr__(self):
        return self.repr_indented()

    def annotate(self, context, expected_type):
        self.terms = [term.annotate(context, None) if isinstance(term, AstNode) else term for term in self.terms]
        return self

    def compile(self):
        terms = [t for term in self.terms for t in (term.compile() if isinstance(term, AstNode) else [term])]
        return [WasmExpr(terms)]

    def repr_indented(self, level=0):
        indent = "    " * level
        if len(self.terms) == 1 and not isinstance(self.terms[0], WasmExpr):
            return f"{indent}({self.terms[0]})"
        else:
            terms = []
            if self.terms:
                terms.append(
                    "\n" + self.terms[0].repr_indented(level + 1)
                    if isinstance(self.terms[0], WasmExpr)
                    else str(self.terms[0])
                )
                n = 1
                if (
                    len(self.terms) > 1
                    and self.terms[0] != "elem"
                    and isinstance(self.terms[1], str)
                    and self.terms[1].startswith("$")
                ):
                    terms[0] += " " + self.terms[1]
                    n += 1
                for term in self.terms[n:]:
                    terms.append(
                        term.repr_indented(level + 1) if isinstance(term, WasmExpr) else f"{'    ' * (level + 1)}{term}"
                    )
            inner = "\n".join(terms)
            if len(inner) < 100:
                return indent + self._repr_flat()
            return f"{indent}({inner}\n{indent})"

    def _repr_flat(self):
        return f"({' '.join(map(str, self.terms))})"


class Asm(AstNode):
    def __init__(self, expr):
        self.expr = expr

    def repr_indented(self, level=0):
        return "\n".join(term.repr_indented(level) for term in self.expr.terms)

    def annotate(self, context, expected_type):
        self.expr = self.expr.annotate(context, None)
        return self

    def compile(self) -> list[WasmExpr]:
        return [t for term in self.expr.terms for t in (term.compile() if isinstance(term, AstNode) else [term])]
