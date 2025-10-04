from .ast import AstNode
from .wast import WasmExpr
from .tuple import TupleDecl


class TypeDef(AstNode):
    def __init__(self, name, body):
        self.name = name
        self.body = body
        self.dimensions = ()

    def annotate(self, context):
        for i, expr in enumerate(self.body):
            self.body[i] = expr.annotate(context)

        assert len(self.body) == 1, self.name

        if isinstance(self.body[0], NativeType):
            return self.body[0]

        return self

    def declaration(self):
        compiled_expr = []
        for expr in self.body:
            if isinstance(expr, TypeName) and not expr.dimensions:
                return [WasmExpr([expr.name])]

            compiled_expr.extend(expr.declaration())
        return [WasmExpr(["type", f"${self.name}", *compiled_expr])]

    def instantiation(self, compiled_args):
        assert len(self.body) == 1

        match self.body[0]:
            case TupleDecl():
                return [WasmExpr(["struct.new", f"${self.name}", *compiled_args])]
            case ArrayType():
                return [WasmExpr(["array.new", f"${self.name}", *compiled_args])]

        return self.body[0].instantiation(compiled_args)

    def compile(self):
        return [WasmExpr(["ref", f"${self.name}"])]


class NativeType(AstNode):
    def __init__(self, name):
        self.name = name

    def annotate(self, context):
        return self

    def declaration(self):
        return []

    def compile(self):
        return [self.name]


class TypeName(AstNode):
    def __init__(self, name):
        self.name = name

    def annotate(self, context):
        type_ = context.lookup_type(self.name)
        while isinstance(type_, TypeName):
            type_ = context.lookup_type(type_.name)

        return type_

    def compile(self):
        raise NotImplementedError


class ArrayType(AstNode):
    def __init__(self, name, dimensions):
        self.name = name
        self.dimensions = dimensions

    def annotate(self, context):
        return self

    def declaration(self):
        return [WasmExpr(["array", WasmExpr(["mut", self.name])])]

    def compile(self):
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

        return self.type_.instantiation(compiled_args)
