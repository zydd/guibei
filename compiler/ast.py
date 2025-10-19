from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict


@dataclass(repr=False)
class Node:
    def __iter__(self):
        return iter(self.__dict__.keys())

    def __getitem__(self, i):
        return getattr(self, i)

    def __setitem__(self, i, value):
        return setattr(self, i, value)

    def __repr__(self):
        return f"ast.{self.__class__.__name__}"


@dataclass(repr=False)
class NewType(Node):
    pass


@dataclass(repr=False)
class TypeDef(Node):
    name: str
    super_: NewType


@dataclass(repr=False)
class TupleType(NewType):
    field_types: list[NewType]


@dataclass(repr=False)
class ArrayType(NewType):
    element_type: NewType


@dataclass(repr=False)
class NativeType(NewType):
    args: list[str]


@dataclass(repr=False)
class VoidType(NewType):
    pass


@dataclass(repr=False)
class TypeIdentifier(Node):
    name: str

    def __repr__(self):
        return f"TypeIdentifier({self.name})"


@dataclass(repr=False)
class ArrayIndex(Node):
    array: Node
    idx: Node


@dataclass(repr=False)
class TypeInstantiation(Node):
    type_: NewType
    args: list[Node]


@dataclass(repr=False)
class TypeImpl(Node):
    type_name: str
    methods: list[Node]


@dataclass(repr=False)
class TupleIndex(Node):
    tuple_: Node
    idx: int


@dataclass(repr=False)
class IfStatement(Node):
    condition: Node
    body_then: list[Node]
    body_else: list[Node]


@dataclass(repr=False)
class WhileStatement(Node):
    condition: Node
    body: list[Node]


@dataclass(repr=False)
class ReturnStatement(Node):
    expr: Node


@dataclass(repr=False)
class Assignment(Node):
    lvalue: Node
    expr: Node


@dataclass(repr=False)
class IntLiteral(Node):
    value: int


@dataclass(repr=False)
class StringLiteral(Node):
    value_str: str


@dataclass(repr=False)
class Identifier(Node):
    name: str


@dataclass(repr=False)
class EnumValueType(TupleType):
    name: str


@dataclass(repr=False)
class EnumType(NewType):
    name: str
    values: list[EnumValueType]


@dataclass(repr=False)
class EnumConst(Node):
    type_: NewType
    name: str
    idx: int


@dataclass(repr=False)
class EnumTupleType(TupleType):
    idx: int


@dataclass(repr=False)
class Asm(Node):
    expr: list[WasmExpr]


@dataclass(repr=False)
class WasmExpr(Node):
    terms: list[WasmExpr]


@dataclass(repr=False)
class VarDecl(Node):
    name: str
    type_: NewType
    init: Node


@dataclass(repr=False)
class ArgDecl(Node):
    name: str
    type_: NewType


@dataclass(repr=False)
class FunctionType(NewType):
    args: list[ArgDecl]
    ret_type: NewType


@dataclass(repr=False)
class FunctionDef(Node):
    name: str
    type_: FunctionType
    body: list[Node]


@dataclass(repr=False)
class Call(Node):
    callee: Node
    args: list[Node]


@dataclass(repr=False)
class BoundMethod(Node):
    obj: Node
    func: FunctionDef


@dataclass(repr=False)
class MemberAccess(Node):
    expr: Node
    attr: str


@dataclass(repr=False)
class FunctionCall(Node):
    func: FunctionDef
    args: list[Node]


@dataclass(repr=False)
class CastExpr(Node):
    type_: NewType
    expr: Node


@dataclass(repr=False)
class Module(Node):
    stmts: list[Node]

    def __init__(self, stmts: list[Node]):
        self.stmts = stmts


# class NewType(AstNode):
#     def __init__(self, name, super_):
#         self.name: str = name
#         self.super_: NewType = super_
#         self.method_defs = list()
#         self.methods: dict[str] = dict()
#         self.annotated = False
#         self.vtable = list()
#         self.vtable_name = f"${self.name}_vt"

#     def annotate(self, context, expected_type):
#         if self.annotated:
#             return self
#         self.annotated = True

#         context = context.new()
#         context.types["Self"] = self

#         if self.super_:
#             if not isinstance(self.super_, NewType):
#                 self.super_ = self.super_.annotate(context, None)

#             if self.super_.name is None:
#                 self.super_.name = self.name
#                 self.super_.method_defs = self.method_defs
#                 assert not self.super_.methods
#                 return self.super_.annotate(context, None)
#             else:
#                 self.super_ = self.super_.annotate(context, None)

#         for method in self.method_defs:
#             self.add_method(context, method)

#         return self

#     def add_method(self, context, method):
#         if type(method).__name__ == "FunctionDef":
#             method_attr_name = method.name
#             method.name = f"{self.name}.{method_attr_name}"
#             method.type_.name = f"__method_{self.name}.{method_attr_name}_t"

#             assert method_attr_name not in self.methods
#             self.methods[method_attr_name] = method.annotate(context, None)
#         else:
#             raise NotImplementedError

#     def primitive(self):
#         return self.super_.primitive()

#     def declaration(self):
#         res = []

#         for m in self.methods.values():
#             if isinstance(m, NewType):
#                 res.extend(m.declaration())

#         for m in self.methods.values():
#             if not isinstance(m, NewType):
#                 res.extend(m.declaration())

#         if self.vtable:
#             res.append(WasmExpr(["table", self.vtable_name, "funcref", ["elem", *[f"${fn}" for fn in self.vtable]]]))

#         return res

#     def instantiate(self, compiled_args):
#         return self.super_.instantiate(compiled_args)

#     def compile(self):
#         return self.super_.compile()

#     def check_type(self, expected_type):
#         if isinstance(expected_type, TypeIdentifier):
#             expected_type = expected_type.type_

#         if expected_type:
#             cur = self

#             while cur:
#                 if cur == expected_type:
#                     break
#                 cur = cur.super_
#             else:
#                 raise TypeError("Expected type {}, got {}".format(expected_type.name, self.name))


# class TupleType(NewType):
#     def __init__(self, name, field_types):
#         super().__init__(name, None)
#         self.field_types = field_types

#     def annotate(self, context, expected_type):
#         if len(self.field_types) == 0:
#             return VoidType(self.name)

#         self.field_types = [type_.annotate(context, None) for type_ in self.field_types]
#         return super().annotate(context, expected_type)

#     def primitive(self):
#         return self

#     def declaration(self):
#         fields = []
#         for type_ in self.field_types:
#             fields.append(WasmExpr(["field", *type_.compile()]))
#         struct = WasmExpr(["struct", *fields])
#         if self.super_:
#             struct = WasmExpr(["sub", f"${self.super_.name}", struct])

#         decl = [WasmExpr(["type", f"${self.name}", struct])]
#         return decl + super().declaration()

#     def instantiate(self, compiled_args):
#         return [WasmExpr(["struct.new", f"${self.name}", *compiled_args])]

#     def compile(self):
#         return [WasmExpr(["ref", f"${self.name}"])]


# class ArrayType(NewType):
#     def __init__(self, element_type):
#         super().__init__(None, None)
#         self.element_type = element_type

#     def annotate(self, context, expected_type):
#         self.element_type = self.element_type.annotate(context, None)
#         return super().annotate(context, expected_type)

#     def primitive(self):
#         return self

#     def declaration(self):
#         return [
#             WasmExpr(["type", f"${self.name}", ["array", ["mut", *self.element_type.compile()]]])
#         ] + super().declaration()

#     def instantiate(self, compiled_args):
#         return [WasmExpr(["array.new", f"${self.name}", *compiled_args])]

#     def compile(self):
#         return [WasmExpr(["ref", f"${self.name}"])]


# class NativeType(NewType):
#     def __init__(self, name: str):
#         super().__init__(name, None)

#     def annotate(self, context, expected_type):
#         return self

#     def primitive(self):
#         return self

#     def declaration(self):
#         return []

#     def compile(self):
#         return [self.name]

#     def instantiate(self, value):
#         assert len(value) == 1
#         # FIXME: should replace `instantiate` with proper constructors
#         if isinstance(value[0], WasmExpr):
#             return value
#         return [WasmExpr([f"{self.name}.const", str(value[0])])]

#     def __eq__(self, value):
#         if isinstance(value, NativeType):
#             return self.name == value.name
#         else:
#             return super().__eq__(value)


# class VoidType(NewType):
#     def __init__(self, name="()"):
#         super().__init__(name, None)

#     def annotate(self, context, expected_type):
#         if expected_type and not isinstance(expected_type, VoidType):
#             raise TypeError
#         return self

#     def declaration(self):
#         return []

#     def compile(self):
#         return []

#     def primitive(self):
#         return self


# class TypeIdentifier(NewType):
#     def __init__(self, name):
#         self.name = name
#         self.type_: NewType = None

#     def annotate(self, context, expected_type):
#         type_ = context.lookup_type(self.name)
#         while isinstance(type_, TypeIdentifier):
#             type_ = context.lookup_type(type_.name)
#         self.type_ = type_
#         self.name = type_.name
#         return self

#     def primitive(self):
#         return self.type_.primitive()

#     def compile(self):
#         return self.type_.compile()

#     def check_type(self, expected_type):
#         return self.type_.check_type(expected_type)

#     def __eq__(self, value):
#         while isinstance(value, TypeIdentifier):
#             value = value.type_
#         return self.type_ == value

#     @property
#     def methods(self):
#         return self.type_.methods

#     @property
#     def super_(self):
#         return self.type_.super_


# class ArrayIndex(AstNode):
#     def __init__(self, array, idx):
#         self.array = array
#         self.idx = idx
#         self.type_ = None

#     def annotate(self, context, expected_type):
#         self.array = self.array.annotate(context, None)
#         if self.idx:
#             self.idx = self.idx.annotate(context, NativeType("i32"))
#         self.type_ = self.array.type_.primitive().element_type
#         self.type_.check_type(expected_type)
#         return self

#     def compile(self):
#         match self.type_.primitive():
#             case NativeType(name="i8"):
#                 instr = "array.get_s"
#             case _:
#                 instr = "array.get"
#         return [WasmExpr([instr, f"${self.array.type_.name}", *self.array.compile(), *self.idx.compile()])]

#     def assign(self, compiled_expr):
#         return [
#             WasmExpr(
#                 ["array.set", f"${self.array.type_.name}", *self.array.compile(), *self.idx.compile(), *compiled_expr]
#             )
#         ]


# class TypeInstantiation(AstNode):
#     def __init__(self, type_, args):
#         self.type_ = type_
#         self.args = args

#     def annotate(self, context, expected_type):
#         self.type_.check_type(expected_type)

#         # TODO: invoke constructor
#         self.args = [arg.annotate(context, NativeType("i32")) for arg in self.args]
#         return self

#     def compile(self):
#         compiled_args = []
#         for arg in self.args:
#             result = arg.compile()
#             compiled_args.extend(result)

#         return self.type_.instantiate(compiled_args)


# class TypeImpl(AstNode):
#     def __init__(self, type_name, methods):
#         self.type_name = type_name
#         self.methods = methods

#     def register_methods(self, context):
#         type_ = context.lookup_type(self.type_name)
#         type_.method_defs = self.methods

#     def annotate(self, context, expected_type):
#         raise NotImplementedError

#     def compile(self):
#         raise NotImplementedError


# class TupleIndex(AstNode):
#     def __init__(self, tuple_, idx):
#         self.tuple_ = tuple_
#         self.idx = idx
#         self.type_ = None

#     def annotate(self, context, expected_type):
#         self.tuple_ = self.tuple_.annotate(context, None)
#         self.type_ = self.tuple_.type_.primitive().field_types[self.idx]
#         self.type_.check_type(expected_type)
#         return self

#     def compile(self):
#         return [WasmExpr(["struct.get", f"${self.tuple_.type_.name}", str(self.idx), *self.tuple_.compile()])]


# class IfStatement(AstNode):
#     def __init__(self, condition, body_then, body_else):
#         self.condition = condition
#         self.body_then = body_then
#         self.body_else = body_else
#         self.type_ = VoidType()

#     def annotate(self, context, expected_type):
#         self.condition = self.condition.annotate(context, NativeType("i32"))
#         self.body_then = [expr.annotate(context, None) for expr in self.body_then]
#         self.body_else = [expr.annotate(context, None) for expr in self.body_else]
#         return self

#     def compile(self):
#         body_then = []
#         body_else = []

#         for stmt in self.body_then:
#             body_then.extend(stmt.compile())

#         for stmt in self.body_else:
#             body_else.extend(stmt.compile())

#         res = [
#             "if",
#             *self.condition.compile(),
#             [
#                 "then",
#                 *body_then,
#             ],
#         ]

#         if self.body_else:
#             res.append(["else", *body_else])

#         return [WasmExpr(res)]


# class WhileStatement(AstNode):
#     def __init__(self, condition, body):
#         self.condition = condition
#         self.body = body
#         self.type_ = VoidType()

#     def annotate(self, context, expected_type):
#         self.condition = self.condition.annotate(context, NativeType("i32"))
#         self.body = [expr.annotate(context, None) for expr in self.body]
#         return self

#     def compile(self):
#         body = []
#         for stmt in self.body:
#             body.extend(stmt.compile())
#         id = AstNode.next_id()
#         return [
#             WasmExpr(
#                 [
#                     "block",
#                     f"$while_block_{id}",
#                     [
#                         "loop",
#                         f"$while_loop_{id}",
#                         [
#                             "br_if",
#                             f"$while_block_{id}",
#                             ["i32.eqz", *self.condition.compile()],
#                         ],
#                         *body,
#                         ["br", f"$while_loop_{id}"],
#                     ],
#                 ]
#             )
#         ]


# class ReturnStatement(AstNode):
#     def __init__(self, expr):
#         self.expr = expr
#         self.type_ = VoidType()

#     def annotate(self, context, expected_type):
#         # self.type_.check_type(expected_type)
#         self.expr = self.expr.annotate(context, context.current_function().type_.ret_type)
#         return self

#     def compile(self):
#         return [WasmExpr(["return", *self.expr.compile()])]


# class Assignment(AstNode):
#     def __init__(self, lvalue, expr):
#         self.lvalue = lvalue
#         self.expr = expr
#         self.type_ = VoidType()

#     def annotate(self, context, expected_type):
#         self.lvalue = self.lvalue.annotate(context, None)
#         self.expr = self.expr.annotate(context, self.lvalue.type_)
#         if self.lvalue.type_ and self.expr.type_:
#             self.lvalue.type_.check_type(self.expr.type_)
#         return self

#     def compile(self):
#         return self.lvalue.assign(self.expr.compile())


# class IntLiteral(AstNode):
#     def __init__(self, value: int):
#         self.value = value
#         self.type_ = None

#     def annotate(self, context, expected_type):
#         self.type_ = expected_type
#         return self

#     def compile(self):
#         return self.type_.primitive().instantiate([self.value])

#     def __repr__(self):
#         return repr(self.value)


# class StringLiteral(AstNode):
#     def __init__(self, value: str):
#         self.value_str = value
#         self.value = value.encode().decode("unicode_escape").encode()
#         self.addr = None
#         self.type_ = None
#         self.temp_var_name = None

#     def annotate(self, context, expected_type):
#         self.addr = context.add_data(self.value)
#         self.type_ = expected_type
#         self.temp_var_name = f"__local_{self.next_id()}"
#         context.register_variable(VarDecl(self.temp_var_name, self.type_, annotated=True))
#         return self

#     def compile(self):
#         return [
#             WasmExpr(
#                 [
#                     f"local.tee ${self.temp_var_name}",
#                     [f"array.new_default ${self.type_.name}", f"(i32.const {len(self.value)})"],
#                 ]
#             ),
#             *(
#                 WasmExpr(
#                     [
#                         f"array.set ${self.type_.name} (local.get ${self.temp_var_name}) (i32.const {i}) (i32.const {byte})"
#                     ]
#                 )
#                 for i, byte in enumerate(self.value)
#             ),
#         ]

#     def __repr__(self):
#         return f'"{self.value_str}"'


# class Identifier(AstNode):
#     def __init__(self, name: str):
#         for i, c in enumerate(operator_characters):
#             name = name.replace(c, f"${i}")

#         self.name = name
#         self.type_ = None

#     def annotate(self, context, expected_type):
#         if expected_type:
#             return context.lookup_var(self.name)
#         else:
#             return context.lookup(self.name)

#     def compile(self):
#         return [WasmExpr(["local.get", f"${self.name}"])]

#     def __repr__(self):
#         return f"Id({self.name})"


# class Enum(NewType):
#     def __init__(self, name, values):
#         super().__init__(name, None)
#         self.value_defs = values
#         self.value_types = None

#     def annotate(self, context, expected_type):
#         context = context.new()
#         context.types["Self"] = self

#         self.value_types = []
#         for i, (value_name, fields) in enumerate(self.value_defs):
#             value_type_name = f"{self.name}.{value_name}"
#             if fields:
#                 val_type = EnumTupleType(value_type_name, fields, i)
#             else:
#                 val_type = NewType(value_type_name, None)
#                 context.register_const(EnumConst(val_type, value_name, i))

#             val_type.annotate(context, None)
#             val_type.super_ = self
#             self.value_types.append(val_type)
#             self.methods[value_name] = val_type

#         self._annotate_methods(context)

#         return self

#     def _annotate_methods(self, context):
#         method_overloads = defaultdict(list)
#         for m in self.method_defs:
#             method_overloads[m.name].append(m)

#         generic_methods = {}

#         # Add methods
#         for method_name, overloads in method_overloads.items():
#             overload_arg_names = [[arg_name for arg_name, arg_type in m.type_.args] for m in overloads]
#             overload_arg_types = [
#                 [arg_type.annotate(context, None) for arg_name, arg_type in m.type_.args] for m in overloads
#             ]

#             if not overload_arg_names or not overload_arg_names[0][0] == "self":
#                 raise NotImplementedError("Static methods are not supported, first argument must be 'self'")

#             # Check if all arg_names are the same
#             if not all(overload_arg_names[0] == args for args in overload_arg_names):
#                 raise ValueError(f"Argument names for method '{self.name}.{method_name}' overloads do not match")

#             self_arg_types = [args[0] for args in overload_arg_types]
#             if not all(arg_type in self.value_types or arg_type == self for arg_type in self_arg_types):
#                 raise ValueError(f"Unexpected 'self' type for method '{self.name}.{method_name}'")

#             try:
#                 generic_method = overloads[self_arg_types.index(self)]
#                 generic_method.name = "__generic." + generic_method.name
#                 self.add_method(context, generic_method)
#                 generic_methods[method_name] = generic_method
#             except ValueError:
#                 generic_method = None

#             for enum_val_type in self.value_types:
#                 try:
#                     specialized_method = overloads[self_arg_types.index(enum_val_type)]
#                 except ValueError:
#                     # No specialization
#                     specialized_method = None

#                 if specialized_method:
#                     # TODO: should generate new methods?
#                     specialized_method.cast_self_from_any = True
#                     enum_val_type.add_method(context, specialized_method)
#                 elif generic_method:
#                     # TODO: Does it make sense to add the generic method to the value types?
#                     pass
#                 else:
#                     raise ValueError(f"No implementation for method '{enum_val_type.name}.{method_name}'")

#         # Create vtable
#         for enum_val_type in self.value_types:
#             for method_name in method_overloads:
#                 if method_name in enum_val_type.methods:
#                     self.vtable.append(enum_val_type.methods[method_name].name)
#                 else:
#                     self.vtable.append(generic_methods[method_name].name)

#         # Create dispatch function
#         for method_idx, method_name in enumerate(method_overloads):
#             generic_method = generic_methods[method_name]
#             dispatch = WasmExpr(
#                 [
#                     *(f"(local.get ${arg})" for arg,  in generic_method.type_.args),
#                     [
#                         "block",
#                         "(result (ref i31))",
#                         f"(br_on_cast 0 (ref any) (ref i31) (local.get $self))",
#                         f"(ref.cast (ref ${self.name}))",
#                         f"(struct.get ${self.name} 0)",
#                     ],
#                     "(i31.get_u)",
#                     f"(i32.mul (i32.const {len(method_overloads)}))",
#                     f"(i32.add (i32.const {method_idx}))",
#                     f"(return_call_indirect {self.vtable_name} (type ${generic_method.type_.name}))",
#                 ]
#             )
#             method = FunctionDef(
#                 method_name,
#                 generic_methods[method_name].type_.args,
#                 generic_methods[method_name].type_.ret_type,
#                 [Asm(dispatch)],
#             )
#             self.add_method(context, method)

#     def declaration(self):
#         defs = [WasmExpr(["type", f"${self.name}", "(sub (struct (field (ref i31))))"])]
#         return defs + super().declaration()

#     def compile(self):
#         return [WasmExpr(["ref any"])]


# class EnumConst(AstNode):
#     def __init__(self, type_, name, idx):
#         self.name = name
#         self.idx = idx
#         self.type_ = type_

#     def annotate(self, context, expected_type):
#         return self

#     def compile(self):
#         return [WasmExpr(["ref.i31", ["i32.const", str(self.idx)]])]


# class EnumTupleType(TupleType):
#     def __init__(self, name, fields, idx):
#         fields.insert(0, NativeType("(ref i31)"))
#         super().__init__(name, fields)
#         self.idx = idx

#     def instantiate(self, compiled_args):
#         return [
#             WasmExpr(
#                 [
#                     "struct.new",
#                     f"${self.name}",
#                     ["ref.i31", ["i32.const", self.idx]],
#                     *compiled_args,
#                 ]
#             )
#         ]


# class Asm(AstNode):
#     def __init__(self, expr):
#         self.expr = expr
#         self.type_ = None

#     def repr_indented(self, level=0):
#         return "\n".join(term.repr_indented(level) for term in self.expr.terms)

#     def annotate(self, context, expected_type):
#         self.expr = self.expr.annotate(context, None)
#         self.type_ = expected_type
#         return self

#     def compile(self) -> list[WasmExpr]:
#         return [t for term in self.expr.terms for t in (term.compile() if isinstance(term, AstNode) else [term])]


# class VarDecl(AstNode):
#     def __init__(self, name, type_, init=None, mutable=False, annotated=False):
#         self.name = name
#         self.type_ = type_
#         self.init = init
#         self.mutable = mutable
#         self.annotated = annotated

#     def annotate(self, context, expected_type):
#         if self.annotated:
#             return self
#         self.annotated = True
#         self.type_ = self.type_.annotate(context, None)
#         context.register_variable(self)
#         if self.init:
#             self.init = self.init.annotate(context, self.type_)
#             return Assignment(self, self.init)
#         return VoidType()

#     def assign(self, compiled_expr):
#         return [WasmExpr(["local.set", f"${self.name}", *compiled_expr])]

#     def compile(self):
#         return [WasmExpr(["local.get", f"${self.name}"])]


# class FunctionType(NewType):
#     def __init__(self, name, args, ret_type):
#         super().__init__(name, None)
#         self.args = args
#         self.ret_type = ret_type

#     def annotate(self, context, expected_type):
#         self.args = [(arg_name, arg_type.annotate(context, None)) for arg_name, arg_type in self.args]

#         if self.ret_type:
#             self.ret_type = self.ret_type.annotate(context, None)

#         return self

#     def primitive(self):
#         return self

#     def declaration(self):
#         decls = []
#         for arg_name, arg_type in self.args:
#             decls.append(WasmExpr(["param", f"${arg_name}", *arg_type.compile()]))

#         if not isinstance(self.ret_type, VoidType):
#             decls.append(WasmExpr(["result", *self.ret_type.compile()]))

#         type_ = WasmExpr(["func", *decls])
#         if self.name is not None:
#             type_ = WasmExpr(["type", f"${self.name}", type_])
#         return [type_]


# class FunctionDef(AstNode):
#     def __init__(self, name, args, ret_type, body):
#         self.name = name
#         self.type_ = FunctionType(f"__func_{name}_t", args, ret_type)
#         self.body = body
#         self.locals = {}
#         self.cast_self_from_any = False

#     def annotate(self, context, expected_type):
#         context = context.new()
#         context._current_function = self

#         self.type_ = self.type_.annotate(context, expected_type)

#         for i, (arg_name, arg_type) in enumerate(self.type_.args):
#             if arg_name == "self":
#                 arg_type.check_type(context.lookup_type("Self"))
#                 if self.cast_self_from_any and self.body:
#                     cast_var = VarDecl(
#                         "self",
#                         arg_type,
#                         WasmExpr(["ref.cast", *arg_type.compile(), ["local.get", "$__self"]]),
#                         annotated=False,
#                     )
#                     self.body.insert(0, cast_var)

#                     arg_name, arg_type = "__self", NativeType("(ref any)")
#                     self.type_.args[i] = (arg_name, arg_type)

#             assert arg_name not in context.variables
#             context.variables[arg_name] = VarDecl(arg_name, arg_type, annotated=True)

#         for i, expr in enumerate(self.body[:-1]):
#             if isinstance(expr, ReturnStatement):
#                 expr = expr.annotate(context, self.type_.ret_type)
#             else:
#                 expr = expr.annotate(context, None)

#             self.body[i] = expr
#             assert expr is not None, self.body[i]

#         if self.body:
#             expr = self.body[-1]
#             expr = expr.annotate(context, self.type_.ret_type)

#             self.body[-1] = expr
#             assert expr is not None, self.body[i]

#         if hasattr(self, "annotations"):
#             assert self.body == []
#             context.register_import(
#                 WasmExpr(
#                     [
#                         "func",
#                         f"${self.name}",
#                         [self.annotations[0].callee.name, *self.annotations[0].args],
#                         ["type", f"${self.type_.name}"],
#                     ]
#                 )
#             )

#         return self

#     def declaration(self):
#         decls = []
#         for arg_name, arg_type in self.type_.args:
#             decls.append(WasmExpr(["param", f"${arg_name}", *arg_type.compile()]))

#         if not isinstance(self.type_.ret_type, VoidType):
#             decls.append(WasmExpr(["result", *self.type_.ret_type.compile()]))

#         for name, var in self.locals.items():
#             decls.append(WasmExpr(["local", f"${name}", *var.type_.compile()]))

#         body = []
#         for expr in self.body[:-1]:
#             body.extend(expr.compile())

#             if not isinstance(expr, Asm) and not isinstance(expr.type_, VoidType):
#                 body.append(WasmExpr(["drop"]))

#         if self.body:
#             body.extend(self.body[-1].compile())

#             if (
#                 isinstance(self.type_.ret_type, VoidType)
#                 and not isinstance(self.body[-1], Asm)
#                 and not isinstance(self.body[-1].type_, VoidType)
#             ):
#                 body.append(WasmExpr(["drop"]))

#         res = self.type_.declaration()
#         if self.body:
#             res.append(WasmExpr(["func", f"${self.name}", ["type", f"${self.type_.name}"], *decls, *body]))
#         return res

#     def compile(self):
#         raise NotImplementedError


# class Call(AstNode):
#     def __init__(self, callee, args):
#         self.callee = callee
#         self.args = args

#     def annotate(self, context, expected_type):
#         self.callee = self.callee.annotate(context, None)
#         match self.callee:
#             case FunctionDef():
#                 return FunctionCall(self.callee, self.args).annotate(context, expected_type)
#             case BoundMethod():
#                 if self.callee.func.type_.args and self.callee.func.type_.args[0][0] == "self":
#                     self.args = [self.callee.obj] + self.args
#                 return FunctionCall(self.callee.func, self.args).annotate(context, expected_type)
#             case _ if isinstance(self.callee, NewType):
#                 return TypeInstantiation(self.callee, self.args).annotate(context, expected_type)

#         raise TypeError(f"Cannot call non-function '{self.callee}'")

#     def __repr__(self):
#         return f"{self.callee}{tuple(self.args)}"


# class BoundMethod(AstNode):
#     def __init__(self, obj, func):
#         self.func: FunctionDef = func
#         self.obj = obj

#     def annotate(self, context, expected_type):
#         raise NotImplementedError

#     def compile(self):
#         raise NotImplementedError


# class MemberAccess(AstNode):
#     def __init__(self, expr, attr):
#         self.expr = expr
#         self.attr = attr

#     def annotate(self, context, expected_type):
#         self.expr = self.expr.annotate(context, None)

#         if isinstance(self.expr, NewType):
#             assert expected_type is None
#             expr_type = self.expr
#         else:
#             expr_type = self.expr.type_

#         type_ = expr_type
#         method = None
#         while type_ and not method:
#             method = type_.methods.get(self.attr)
#             type_ = type_.super_

#         if not method:
#             raise TypeError(f"Type '{expr_type.name}' has no method '{self.attr}'")

#         match method:
#             case FunctionDef():
#                 method.type_.ret_type.check_type(expected_type)
#                 if isinstance(self.expr, NewType):
#                     return method
#                 else:
#                     return BoundMethod(self.expr, method)
#             case NewType():
#                 assert not expected_type
#                 return method
#         raise NotImplementedError

#     def compile(self):
#         return [WasmExpr(["struct.get", f"${self.expr.type_.name}", str(self.attr), *self.expr.compile()])]


# class FunctionCall(AstNode):
#     def __init__(self, func, args):
#         self.func = func
#         self.args = args
#         self.type_ = func.type_.ret_type

#     def annotate(self, context, expected_type):
#         self.args = [
#             arg_value.annotate(context, arg_type) for arg_value, (, arg_type) in zip(self.args, self.func.type_.args)
#         ]
#         return self

#     def compile(self):
#         args = []
#         for arg in self.args:
#             args.extend(arg.compile())
#         return [WasmExpr(["call", f"${self.func.name}", *args])]


# class CastExpr(AstNode):
#     def __init__(self, type_, expr):
#         self.type_ = type_
#         self.expr = expr

#     def annotate(self, context, expected_type):
#         # self.type_ = self.type_.annotate(context, None)
#         # self.expr = self.type_.annotate(context, None)
#         # TODO: only allow primitive type -> NewType instantiation
#         return Call(self.type_, [self.expr]).annotate(context, expected_type)


# class Module(AstNode):
#     def __init__(self, stmts):
#         self.stmts = stmts

#     def annotate(self, context, expected_type):
#         raise NotImplementedError

#     def compile(self) -> list[WasmExpr]:
#         raise NotADirectoryError
