import compiler.wast as wast


class TypeDef:
    def __init__(self, name, body):
        self.name = name
        self.body = body

    def annotate(self, context):
        return self

    def compile(self) -> list[wast.WasmExpr]:
        expr = []
        for e in self.body:
            # ignore type aliases for now
            if isinstance(e, TypeName) and not e.dimensions:
                return []

            expr.extend(e.declaration())
        return [wast.WasmExpr(["type", f"${self.name}", *expr])]


class TypeName:
    def __init__(self, name, dimensions=()):
        self.name = name
        self.dimensions = dimensions

    def declaration(self):
        if self.dimensions:
            return [wast.WasmExpr(["array", wast.WasmExpr(["mut", self.name])])]
        else:
            return [self.name]

    def compile(self) -> list[wast.WasmExpr]:
        if self.name in ["i32", "i64", "f32"]:
            return [self.name]
        else:
            return [wast.WasmExpr(["ref", f"${self.name}"])]
