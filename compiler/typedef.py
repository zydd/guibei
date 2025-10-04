from .ast import AstNode
from .wast import WasmExpr


class TypeDef(AstNode):
    def __init__(self, name, body):
        self.name = name
        self.body = body
        self.dimensions = ()

    def annotate(self, context):
        for i, expr in enumerate(self.body):
            self.body[i] = expr.annotate(context)

        assert len(self.body) == 1, self.name
        if isinstance(self.body[0], TypeName):
            self.dimensions = self.body[0].dimensions

        return self

    def compile(self):
        compiled_expr = []
        for expr in self.body:
            # ignore type aliases for now
            if isinstance(expr, TypeName) and not expr.dimensions:
                return []

            compiled_expr.extend(expr.declaration())
        return [WasmExpr(["type", f"${self.name}", *compiled_expr])]


class TypeName(AstNode):
    native_types = ["i32", "i8", "i64", "f32"]

    def __init__(self, name, dimensions=()):
        self.name = name
        self.dimensions = dimensions

    def annotate(self, context):
        if self.name in self.native_types:
            return self

        context.lookup_type(self.name)

        return self

    def declaration(self):
        if self.dimensions:
            return [WasmExpr(["array", WasmExpr(["mut", self.name])])]
        else:
            return [self.name]

    def compile(self):
        if self.name in self.native_types:
            return [self.name]
        else:
            return [WasmExpr(["ref", f"${self.name}"])]


class TypeInstantiation:
    def __init__(self, type_, args):
        assert isinstance(type_, TypeDef)
        self.type_ = type_
        self.args = args

    def compile(self):
        compiled_args = []
        for arg in self.args:
            result = arg.compile()
            if isinstance(result, list):
                compiled_args.extend(result)
            else:
                compiled_args.append(result)

        if self.type_.name in ["i32", "i64", "f32"]:
            assert len(self.args) == 1
            return compiled_args
        elif self.type_.dimensions:
            assert len(self.args) == 2
            return [WasmExpr(["array.new", f"${self.type_.name}", *compiled_args])]
        else:
            return [WasmExpr(["struct.new", f"${self.type_.name}", *compiled_args])]
