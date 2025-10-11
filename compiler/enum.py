from compiler.ast import AstNode
from compiler.typedef import NewType, TupleType
from compiler.wast import WasmExpr


class Enum(NewType):
    def __init__(self, name, values):
        super().__init__(name, None)
        self.values = values

    def annotate(self, context, expected_type):
        value_types = []
        for i, (value_name, fields) in enumerate(self.values):
            if fields:
                val_type = TupleType(value_name, fields)
            else:
                val_type = NewType(value_name, None)
                context.register_const(EnumConst(val_type, value_name, i))

            context.register_type(val_type)
            value_types.append(val_type)
            self.methods[value_name] = val_type

        generic_methods = []
        for method in self.method_defs:
            if method.type_.args:
                arg_name, self_type = method.type_.args[0]
                self_type = self_type.annotate(context, None).type_
                if arg_name == "self" and self_type != self:
                    assert self_type in value_types
                    self_type.method_defs.append(method)
                    continue

            generic_methods.append(method)

        self.method_defs = generic_methods

        for val_type in value_types:
            val_type.name = f"{self.name}.{val_type.name}"
            val_type.annotate(context, expected_type)
            val_type.super_ = self

        return super().annotate(context, expected_type)

    def declaration(self):
        return []

    def compile(self):
        return [WasmExpr(["ref any"])]


class EnumConst(AstNode):
    def __init__(self, type_, name, idx):
        self.name = name
        self.idx = idx
        self.type_ = type_

    def annotate(self, context, expected_type):
        return self

    def compile(self):
        return [WasmExpr(["ref.i31", WasmExpr(["i32.const", str(self.idx)])])]
