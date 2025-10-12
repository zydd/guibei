from compiler.ast import AstNode
from compiler.typedef import NewType, TupleType, NativeType
from compiler.wast import WasmExpr


class Enum(NewType):
    def __init__(self, name, values):
        super().__init__(name, None)
        self.values = values

    def annotate(self, context, expected_type):
        value_types = []
        for i, (value_name, fields) in enumerate(self.values):
            if fields:
                val_type = EnumTupleType(value_name, fields, i)
            else:
                val_type = NewType(value_name, None)
                context.register_const(EnumConst(val_type, value_name, i))

            context.register_type(val_type)
            value_types.append(val_type)
            self.methods[value_name] = val_type

        generic_methods = {}
        method_names = set()
        for method in self.method_defs:
            if method.type_.args:
                arg_name, self_type = method.type_.args[0]
                self_type = self_type.annotate(context, None).type_
                if arg_name == "self" and self_type != self:
                    assert self_type in value_types
                    self_type.method_defs.append(method)
                    continue

            method_names.add(method.name)
            assert method.name not in generic_methods
            generic_methods[method.name] = method

        self.method_defs = generic_methods.values()

        for val_type in value_types:
            val_type.name = f"{self.name}.{val_type.name}"
            val_type.annotate(context, expected_type)
            val_type.super_ = self

        res = super().annotate(context, expected_type)
        for m in method_names:
            method = self.methods[m]
            for val_type in value_types:
                if m in val_type.methods:
                    self.vtable.append(val_type.methods[m].name)
                else:
                    self.vtable.append(method)
            # self.methods[m] = EnumVirtualMethod(self.vtable_name, method.type_, )

        return res

    def declaration(self):
        defs = [WasmExpr(["type", f"${self.name}", "(sub (struct (field (ref i31))))"])]
        for method_name, method in self.methods.items():
            if isinstance(method, NewType):
                continue

            defs.append(WasmExpr(["func", f"$__enum_{method_name}"]))
            # TODO: dispatch method
        return defs + super().declaration()

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


class EnumTupleType(TupleType):
    def __init__(self, name, fields, idx):
        fields.insert(0, NativeType("(ref i31)"))
        super().__init__(name, fields)
        self.idx = idx

    def instantiate(self, compiled_args):
        return [
            WasmExpr(
                [
                    "struct.new",
                    f"${self.name}",
                    WasmExpr(["ref.i31", WasmExpr(["i32.const", self.idx])]),
                    *compiled_args,
                ]
            )
        ]

    def compile(self):
        return [WasmExpr(["ref any"])]


class EnumVirtualMethod(AstNode):
    def __init__(self, table, func_type):
        self.table = table
        self.func_type = func_type

    def annotate(self, context, expected_type):
        raise NotImplementedError

    def compile(self):
        # return [WasmExpr(["table.get", self.table, *self.func_type.compile(), WasmExpr("i32.const", self.index)])]
        raise NotImplementedError
