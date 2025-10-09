from compiler.ast import AstNode
from compiler.typedef import NewType, TupleType
from compiler.wast import WasmExpr


class Enum(NewType):
    def __init__(self, name, values):
        super().__init__(name, None)
        self.values = values

    def register_types(self, context):
        for i, (value_name, fields) in enumerate(self.values):
            if fields:
                field_type = TupleType(value_name, fields)
                field_type.super_ = self
                context.register_type(field_type)
            else:
                context.register_const(EnumConst(self, value_name, i))

    def annotate(self, context, expected_type):
        return self

    def declaration(self):
        return []

    def compile(self):
        return [WasmExpr(["ref any"])]


class EnumConst(AstNode):
    def __init__(self, enum, name, idx):
        self.name = name
        self.idx = idx
        self.type_ = enum

    def annotate(self, context, expected_type):
        raise NotImplementedError

    def compile(self):
        return [WasmExpr(["ref.i31", WasmExpr(["i32.const", str(self.idx)])])]

