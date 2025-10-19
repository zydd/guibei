from __future__ import annotations

import copy
import dataclasses
from collections import OrderedDict
from dataclasses import dataclass, field


from . import ast


@dataclass
class Scope:
    parent: Scope | None = None
    vars: dict[str, Node] = field(default_factory=dict)
    types: dict[str, Type] = field(default_factory=dict)
    stmts: list[Node] = field(default_factory=list)

    def register_var(self, name: str, func: Node):
        assert not self.has_member(name)
        self.vars[name] = func

    def register_type(self, name: str, type_: Type):
        assert not self.has_member(name)
        self.types[name] = type_

    def has_member(self, name: str) -> bool:
        return name in self.vars or name in self.types

    def lookup_type(self, name: str) -> Type:
        if name in self.types:
            return self.types[name]
        elif self.parent:
            return self.parent.lookup_type(name)
        else:
            raise KeyError(f"Type '{name}' not found")


@dataclass
class Node:
    ast_node: ast.Node | None

    def __iter__(self):
        return iter(self.__dict__.keys())

    def __getitem__(self, i):
        return getattr(self, i)

    def __setitem__(self, i, value):
        return setattr(self, i, value)

    def __repr__(self):
        return f"ast.{self.__class__.__name__}"

    # def __repr__(self):
    #     fields = ", ".join(
    #         f"{f.name}={getattr(self, f.name)}" for f in dataclasses.fields(self) if f.name != "ast_node"
    #     )
    #     return f"ir.{self.__class__.__name__}({fields})"


@dataclass
class Untranslated(Node):
    def __repr__(self):
        return f"Untranslated({self.ast_node})"


@dataclass
class Module(Node):
    scope: Scope = field(default_factory=Scope)
    asm: list[Node] = field(default_factory=list)
    id_count: int = 0

    def next_id(self):
        self.id_count += 1
        return self.id_count

    def add_asm(self, asm: Node):
        self.asm.append(asm)


@dataclass
class Type(Node):
    pass


@dataclass
class TypeDef(Type):
    super_: Type | None
    name: str
    attributes: dict[str, Node] = field(default_factory=dict)
    methods: dict[str, Node] = field(default_factory=dict)
    types: dict[str, Node] = field(default_factory=dict)

    def add_attribute(self, name: str, attr: Node):
        assert not self.has_member(name)
        self.attributes[name] = attr

    def add_method(self, name: str, method: Node):
        if self.has_member(name):
            # TODO: ensure all overloaded functions/methods are defined together
            assert name in self.methods
            match self.methods[name]:
                case FunctionDef() as fn:
                    self.methods[name] = OverloadedFunction(None, name, [fn, method])
                case OverloadedFunction() as overloads:
                    overloads.overloads.append(method)
                case _:
                    raise NotImplementedError
        else:
            self.methods[name] = method

    def add_type(self, name: str, type_: Node):
        assert not self.has_member(name)
        self.types[name] = type_

    def has_member(self, name: str) -> bool:
        return name in self.attributes or name in self.methods


@dataclass
class UntranslatedType(Type):
    def __repr__(self):
        return f"UntranslatedType({self.ast_node})"

    def translate(self, scope: Scope):
        type_name = type(self.ast_node).__name__
        ir_type = globals().get(type_name)
        if ir_type:
            return ir_type.translate(self.ast_node, scope)
        match self.ast_node:
            case ast.TypeIdentifier():
                type_ = scope.lookup_type(self.ast_node.name)
                return TypeRef(self.ast_node, self.ast_node.name, type_)
        raise NotImplementedError(type_name)


@dataclass(kw_only=True)
class EnumType(TypeDef):
    @staticmethod
    def translate(node: ast.EnumType):
        enum_type = EnumType(node, None, name=node.name)
        for i, val in enumerate(node.values):
            enum_type.add_type(val.name, EnumValueType.translate(enum_type, i, val))
        return enum_type


@dataclass(kw_only=True)
class EnumValueType(TypeDef):
    discr: int
    field_types: list[Type]

    @staticmethod
    def translate(enum: EnumType, discr: int, node: ast.EnumValueType):
        assert isinstance(node, ast.EnumValueType)
        field_types: list = [UntranslatedType(t) for t in node.field_types]
        return EnumValueType(node, TypeRef(None, enum.name, enum), node.name, discr=discr, field_types=field_types)


@dataclass
class ArrayType(Type):
    element_type: Type

    @staticmethod
    def translate(node: ast.ArrayType, scope: Scope):
        return ArrayType(node, UntranslatedType(node.element_type).translate(scope))


@dataclass
class TypeRef(Type):
    name: str
    type_: Type

    def __repr__(self):
        return f"TypeRef({self.name})"


@dataclass
class FunctionType(Type):
    args: list[ArgDecl]
    ret_type: Type

    @staticmethod
    def translate(node: ast.FunctionType):
        args = [ArgDecl(arg, arg.name, UntranslatedType(arg.type_)) for arg in node.args]
        ret_type = UntranslatedType(node.ret_type)
        return FunctionType(node, args, ret_type)


@dataclass
class NativeType(Type):
    name: str
    array_packed: str
    signed: bool | None = None

    @staticmethod
    def translate(node: ast.NativeType, _scope):
        name = node.args[0]
        packed = node.args[1] if len(node.args) > 1 else name
        signed = bool(node.args[2]) if len(node.args) > 2 else None
        return NativeType(node, name, packed, signed)


@dataclass
class ArgDecl(Node):
    name: str
    type_: Type


@dataclass
class FunctionDef(Node):
    type_: Node
    scope: Scope = field(default_factory=Scope)

    @staticmethod
    def translate(node: ast.FunctionDef):
        func_type = FunctionType.translate(node.type_)
        body: list = [Untranslated(stmt) for stmt in node.body]
        return FunctionDef(node, func_type, Scope(stmts=body))


@dataclass
class OverloadedFunction(Node):
    name: str
    overloads: list[Node]
