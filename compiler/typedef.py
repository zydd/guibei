from compiler.ast import AstNode
from compiler.wast import WasmExpr


class NewType(AstNode):
    def __init__(self, name, super_):
        self.name: str = name
        self.super_: NewType = super_
        self.method_defs = list()
        self.methods: dict[str] = dict()
        self.annotated = False
        self.vtable = list()
        self.vtable_name = f"${self.name}_vt"

    def annotate(self, context, expected_type):
        if self.annotated:
            return self
        self.annotated = True

        context = context.new()
        context.types["Self"] = self

        if self.super_:
            if not isinstance(self.super_, NewType):
                self.super_ = self.super_.annotate(context, None)

            if self.super_.name is None:
                self.super_.name = self.name
                self.super_.method_defs = self.method_defs
                assert not self.super_.methods
                return self.super_.annotate(context, None)
            else:
                self.super_ = self.super_.annotate(context, None)

        for method in self.method_defs:
            self.add_method(context, method)

        return self

    def add_method(self, context, method):
        if type(method).__name__ == "FunctionDef":
            method_attr_name = method.name
            method.name = f"{self.name}.{method_attr_name}"
            method.type_.name = f"__method_{self.name}.{method_attr_name}_t"

            assert method_attr_name not in self.methods
            self.methods[method_attr_name] = method.annotate(context, None)
        else:
            raise NotImplementedError

    def primitive(self):
        return self.super_.primitive()

    def declaration(self):
        res = []

        for m in self.methods.values():
            if isinstance(m, NewType):
                res.extend(m.declaration())

        for m in self.methods.values():
            if not isinstance(m, NewType):
                res.extend(m.declaration())

        if self.vtable:
            res.append(WasmExpr(["table", self.vtable_name, "funcref", ["elem", *[f"${fn}" for fn in self.vtable]]]))

        return res

    def instantiate(self, compiled_args):
        return self.super_.instantiate(compiled_args)

    def compile(self):
        return self.super_.compile()

    def check_type(self, expected_type):
        if isinstance(expected_type, TypeIdentifier):
            expected_type = expected_type.type_

        if expected_type:
            cur = self

            while cur:
                if cur == expected_type:
                    break
                cur = cur.super_
            else:
                raise TypeError("Expected type {}, got {}".format(expected_type.name, self.name))


class TupleType(NewType):
    def __init__(self, name, field_types):
        super().__init__(name, None)
        self.field_types = field_types

    def annotate(self, context, expected_type):
        if len(self.field_types) == 0:
            return VoidType(self.name)

        self.field_types = [type_.annotate(context, None) for type_ in self.field_types]
        return super().annotate(context, expected_type)

    def primitive(self):
        return self

    def declaration(self):
        fields = []
        for type_ in self.field_types:
            fields.append(WasmExpr(["field", *type_.compile()]))
        struct = WasmExpr(["struct", *fields])
        if self.super_:
            struct = WasmExpr(["sub", f"${self.super_.name}", struct])

        decl = [WasmExpr(["type", f"${self.name}", struct])]
        return decl + super().declaration()

    def instantiate(self, compiled_args):
        return [WasmExpr(["struct.new", f"${self.name}", *compiled_args])]

    def compile(self):
        return [WasmExpr(["ref", f"${self.name}"])]


class ArrayType(NewType):
    def __init__(self, element_type):
        super().__init__(None, None)
        self.element_type = element_type

    def annotate(self, context, expected_type):
        self.element_type = self.element_type.annotate(context, None)
        return super().annotate(context, expected_type)

    def primitive(self):
        return self

    def declaration(self):
        return [
            WasmExpr(["type", f"${self.name}", ["array", ["mut", *self.element_type.compile()]]])
        ] + super().declaration()

    def instantiate(self, compiled_args):
        return [WasmExpr(["array.new", f"${self.name}", *compiled_args])]

    def compile(self):
        return [WasmExpr(["ref", f"${self.name}"])]


class NativeType(NewType):
    def __init__(self, name: str):
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
        assert len(value) == 1
        # FIXME: should replace `instantiate` with proper constructors
        if isinstance(value[0], WasmExpr):
            return value
        return [WasmExpr([f"{self.name}.const", str(value[0])])]

    def __eq__(self, value):
        if isinstance(value, NativeType):
            return self.name == value.name
        else:
            return super().__eq__(value)


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

    def primitive(self):
        return self


class TypeIdentifier(NewType):
    def __init__(self, name):
        self.name = name
        self.type_: NewType = None

    def annotate(self, context, expected_type):
        type_ = context.lookup_type(self.name)
        while isinstance(type_, TypeIdentifier):
            type_ = context.lookup_type(type_.name)
        self.type_ = type_
        self.name = type_.name
        return self

    def primitive(self):
        return self.type_.primitive()

    def compile(self):
        return self.type_.compile()

    def check_type(self, expected_type):
        return self.type_.check_type(expected_type)

    def __eq__(self, value):
        while isinstance(value, TypeIdentifier):
            value = value.type_
        return self.type_ == value

    @property
    def methods(self):
        return self.type_.methods

    @property
    def super_(self):
        return self.type_.super_


class ArrayIndex(AstNode):
    def __init__(self, array, idx):
        self.array = array
        self.idx = idx
        self.type_ = None

    def annotate(self, context, expected_type):
        self.array = self.array.annotate(context, None)
        if self.idx:
            self.idx = self.idx.annotate(context, NativeType("i32"))
        self.type_ = self.array.type_.primitive().element_type
        self.type_.check_type(expected_type)
        return self

    def compile(self):
        match self.type_.primitive():
            case NativeType(name="i8"):
                instr = "array.get_s"
            case _:
                instr = "array.get"
        return [WasmExpr([instr, f"${self.array.type_.name}", *self.array.compile(), *self.idx.compile()])]

    def assign(self, compiled_expr):
        return [
            WasmExpr(
                ["array.set", f"${self.array.type_.name}", *self.array.compile(), *self.idx.compile(), *compiled_expr]
            )
        ]


class TypeInstantiation(AstNode):
    def __init__(self, type_, args):
        self.type_ = type_
        self.args = args

    def annotate(self, context, expected_type):
        self.type_.check_type(expected_type)

        # TODO: invoke constructor
        self.args = [arg.annotate(context, NativeType("i32")) for arg in self.args]
        return self

    def compile(self):
        compiled_args = []
        for arg in self.args:
            result = arg.compile()
            compiled_args.extend(result)

        return self.type_.instantiate(compiled_args)


class TypeImpl(AstNode):
    def __init__(self, type_name, methods):
        self.type_name = type_name
        self.methods = methods

    def register_methods(self, context):
        type_ = context.lookup_type(self.type_name)
        type_.method_defs = self.methods

    def annotate(self, context, expected_type):
        raise NotImplementedError

    def compile(self):
        raise NotImplementedError
