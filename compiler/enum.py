from collections import defaultdict

from compiler.ast import AstNode
from compiler.typedef import NewType, TupleType, NativeType, TypeIdentifier
from compiler.fndef import FunctionDef
from compiler.wast import WasmExpr, Asm


class Enum(NewType):
    def __init__(self, name, values):
        super().__init__(name, None)
        self.value_defs = values
        self.value_types = None

    def annotate(self, context, expected_type):
        context = context.new()
        context.types["Self"] = self

        self.value_types = []
        for i, (value_name, fields) in enumerate(self.value_defs):
            value_type_name = f"{self.name}.{value_name}"
            if fields:
                val_type = EnumTupleType(value_type_name, fields, i)
            else:
                val_type = NewType(value_type_name, None)
                context.register_const(EnumConst(val_type, value_name, i))

            val_type.annotate(context, None)
            val_type.super_ = self
            self.value_types.append(val_type)
            self.methods[value_name] = val_type

        self._annotate_methods(context)

        return self

    def _annotate_methods(self, context):
        method_overloads = defaultdict(list)
        for m in self.method_defs:
            method_overloads[m.name].append(m)

        generic_methods = {}

        # Add methods
        for method_name, overloads in method_overloads.items():
            overload_arg_names = [[arg_name for arg_name, arg_type in m.type_.args] for m in overloads]
            overload_arg_types = [
                [arg_type.annotate(context, None) for arg_name, arg_type in m.type_.args] for m in overloads
            ]

            if not overload_arg_names or not overload_arg_names[0][0] == "self":
                raise NotImplementedError("Static methods are not supported, first argument must be 'self'")

            # Check if all arg_names are the same
            if not all(overload_arg_names[0] == args for args in overload_arg_names):
                raise ValueError(f"Argument names for method '{self.name}.{method_name}' overloads do not match")

            self_arg_types = [args[0] for args in overload_arg_types]
            if not all(arg_type in self.value_types or arg_type == self for arg_type in self_arg_types):
                raise ValueError(f"Unexpected 'self' type for method '{self.name}.{method_name}'")

            try:
                generic_method = overloads[self_arg_types.index(self)]
                generic_method.name = "__generic." + generic_method.name
                self.add_method(context, generic_method)
                generic_methods[method_name] = generic_method
            except ValueError:
                generic_method = None

            for enum_val_type in self.value_types:
                try:
                    specialized_method = overloads[self_arg_types.index(enum_val_type)]
                except ValueError:
                    # No specialization
                    specialized_method = None

                if specialized_method:
                    # TODO: should generate new methods?
                    specialized_method.cast_self_from_any = True
                    enum_val_type.add_method(context, specialized_method)
                elif generic_method:
                    # TODO: Does it make sense to add the generic method to the value types?
                    pass
                else:
                    raise ValueError(f"No implementation for method '{enum_val_type.name}.{method_name}'")

        # Create vtable
        for enum_val_type in self.value_types:
            for method_name in method_overloads:
                if method_name in enum_val_type.methods:
                    self.vtable.append(enum_val_type.methods[method_name].name)
                else:
                    self.vtable.append(generic_methods[method_name].name)

        # Create dispatch function
        for method_idx, method_name in enumerate(method_overloads):
            generic_method = generic_methods[method_name]
            dispatch = WasmExpr(
                [
                    *(f"(local.get ${arg})" for arg, _ in generic_method.type_.args),
                    [
                        "block",
                        "(result (ref i31))",
                        f"(br_on_cast 0 (ref any) (ref i31) (local.get $self))",
                        f"(ref.cast (ref ${self.name}))",
                        f"(struct.get ${self.name} 0)",
                    ],
                    "(i31.get_u)",
                    f"(i32.mul (i32.const {len(method_overloads)}))",
                    f"(i32.add (i32.const {method_idx}))",
                    f"(return_call_indirect {self.vtable_name} (type ${generic_method.type_.name}))",
                ]
            )
            method = FunctionDef(
                method_name,
                generic_methods[method_name].type_.args,
                generic_methods[method_name].type_.ret_type,
                [Asm(dispatch)],
            )
            self.add_method(context, method)

    def declaration(self):
        defs = [WasmExpr(["type", f"${self.name}", "(sub (struct (field (ref i31))))"])]
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


class EnumVirtualMethod(AstNode):
    def __init__(self, table, func_type):
        self.table = table
        self.func_type = func_type

    def annotate(self, context, expected_type):
        raise NotImplementedError

    def compile(self):
        # return [WasmExpr(["table.get", self.table, *self.func_type.compile(), WasmExpr("i32.const", self.index)])]
        raise NotImplementedError
