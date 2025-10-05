from .ast import AstNode
from .wast import WasmExpr
from .tuple import TupleDecl


class TypeDef(AstNode):
    def __init__(self, name, body):
        self.name = name
        self.body = body
        self.dimensions = ()

    def annotate(self, context, expected_type):
        for i, expr in enumerate(self.body):
            self.body[i] = expr.annotate(context, None)

        assert len(self.body) == 1, self.name
        return self
    
    def root_type(self):
        return self.body[0].root_type()

    def declaration(self):
        if isinstance(self.root_type(), NativeType):
            return []

        compiled_expr = []
        for expr in self.body:
            compiled_expr.extend(expr.declaration())
        return [WasmExpr(["type", f"${self.name}", *compiled_expr])]

    def instantiation(self, compiled_args):
        match self.body[0]:
            case TupleDecl():
                return [WasmExpr(["struct.new", f"${self.name}", *compiled_args])]
            case ArrayType():
                return [WasmExpr(["array.new", f"${self.name}", *compiled_args])]

        return self.body[0].instantiation(compiled_args)

    def compile(self):
        if isinstance(self.body[0], NativeType):
            return self.body[0].compile()

        return [WasmExpr(["ref", f"${self.name}"])]


class NativeType(AstNode):
    def __init__(self, name):
        self.name = name

    def annotate(self, context, expected_type):
        return self
    
    def root_type(self):
        return self

    def declaration(self):
        return []

    def compile(self):
        return [self.name]

    def compile_literal(self, value):
        return [WasmExpr([f"{self.name}.const", str(value)])]


class TypeIdentifier(AstNode):
    def __init__(self, name):
        self.name = name

    def annotate(self, context, expected_type):
        type_ = context.lookup_type(self.name)
        while isinstance(type_, TypeIdentifier):
            type_ = context.lookup_type(type_.name)
        return type_


class ArrayType(AstNode):
    def __init__(self, element_type, dimensions):
        self.element_type = element_type
        self.dimensions = dimensions

    def annotate(self, context, expected_type):
        self.element_type = self.element_type.annotate(context, None)
        return self
    
    def root_type(self):
        return self

    def declaration(self):
        return [WasmExpr(["array", WasmExpr(["mut", *self.element_type.compile()])])]

    def compile(self):
        return [WasmExpr(["ref", f"${self.name}"])]


class ArrayIndex(AstNode):
    def __init__(self, array, idx):
        self.array = array
        self.idx = idx

    def annotate(self, context, expected_type):
        self.array = self.array.annotate(context, None)
        self.idx = self.idx.annotate(context, NativeType("i32"))
        return self

    def compile(self):
        match self.array.type_.root_type().element_type.root_type():
            case NativeType(name="i8"):
                instr = "array.get_s"
            case _:
                instr = "array.get"
        return [WasmExpr([instr, f"${self.array.type_.name}", *self.array.compile(), *self.idx.compile()])]


class TypeInstantiation:
    def __init__(self, type_, args):
        assert isinstance(type_, TypeDef)
        self.type_ = type_
        self.args = args

    def annotate(self, context, expected_type):
        self.args = [arg.annotate(context, NativeType("i32")) for arg in self.args]
        return self

    def compile(self):
        compiled_args = []
        for arg in self.args:
            result = arg.compile()
            compiled_args.extend(result)

        return self.type_.instantiation(compiled_args)


class VoidType(AstNode):
    def annotate(self, context, expected_type):
        if expected_type and expected_type != VoidType:
            raise TypeError
        return self
