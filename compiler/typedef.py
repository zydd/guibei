from .ast import AstNode
from .wast import WasmExpr


class NewType(AstNode):
    def __init__(self, name, super_):
        self.name = name
        self.super_ = super_

    def annotate(self, context, expected_type):
        if self.super_.name is None:
            self.super_.name = self.name
            return self.super_.annotate(context, None)
        else:
            self.super_ = self.super_.annotate(context, None)
            return self

    def primitive(self):
        return self.super_.primitive()

    def declaration(self):
        return self.super_.declaration()

    def instantiate(self, compiled_args):
        return self.super_.instantiate(compiled_args)

    def compile(self):
        return self.super_.compile()


class TupleType(NewType):
    def __init__(self, name, field_types):
        super().__init__(name, None)
        self.field_types = field_types

    def annotate(self, context, expected_type):
        if len(self.field_types) == 0:
            return VoidType(self.name)

        self.field_types = [type_.annotate(context, None) for type_ in self.field_types]
        return self

    def primitive(self):
        return self

    def declaration(self):
        fields = []
        for type_ in self.field_types:
            fields.append(WasmExpr(["field", *type_.compile()]))
        return [WasmExpr(["type", f"${self.name}", WasmExpr(["struct", *fields])])]

    def instantiate(self, compiled_args):
        return [WasmExpr(["struct.new", f"${self.name}", *compiled_args])]

    def compile(self):
        return [WasmExpr(["ref", f"${self.name}"])]


class ArrayType(NewType):
    def __init__(self, name, element_type):
        super().__init__(name, None)
        self.element_type = element_type

    def annotate(self, context, expected_type):
        self.element_type = self.element_type.annotate(context, None)
        return self

    def primitive(self):
        return self

    def declaration(self):
        return [WasmExpr(["type", f"${self.name}", WasmExpr(["array", WasmExpr(["mut", *self.element_type.compile()])])])]

    def instantiate(self, compiled_args):
        return [WasmExpr(["array.new", f"${self.name}", *compiled_args])]

    def compile(self):
        return [WasmExpr(["ref", f"${self.name}"])]


class NativeType(NewType):
    def __init__(self, name):
        super().__init__(name, None)

    def annotate(self, context, expected_type):
        return self

    def primitive(self):
        return self

    def declaration(self):
        return []

    def compile(self):
        return [self.name]

    def instantiate(self, value):
        return [WasmExpr([f"{self.name}.const", str(value)])]


class VoidType(NewType):
    def __init__(self, name="()"):
        super().__init__(name, None)

    def annotate(self, context, expected_type):
        if expected_type and not isinstance(expected_type, VoidType):
            raise TypeError
        return self

    def declaration(self):
        return []

    def compile(self):
        return []


class TypeIdentifier(AstNode):
    def __init__(self, name):
        self.name = name

    def annotate(self, context, expected_type):
        type_ = context.lookup_type(self.name)
        while isinstance(type_, TypeIdentifier):
            type_ = context.lookup_type(type_.name)
        return type_


class ArrayIndex(AstNode):
    def __init__(self, array, idx):
        self.array = array
        self.idx = idx

    def annotate(self, context, expected_type):
        self.array = self.array.annotate(context, None)
        self.idx = self.idx.annotate(context, NativeType("i32"))
        return self

    def compile(self):
        match self.array.type_.primitive().element_type.primitive():
            case NativeType(name="i8"):
                instr = "array.get_s"
            case _:
                instr = "array.get"
        return [WasmExpr([instr, f"${self.array.type_.name}", *self.array.compile(), *self.idx.compile()])]


class TypeInstantiation(AstNode):
    def __init__(self, type_, args):
        self.type_ = type_
        self.args = args

    def annotate(self, context, expected_type):
        self.check_type(self.type_, expected_type)

        self.args = [arg.annotate(context, NativeType("i32")) for arg in self.args]
        return self

    def compile(self):
        compiled_args = []
        for arg in self.args:
            result = arg.compile()
            compiled_args.extend(result)

        return self.type_.instantiate(compiled_args)
