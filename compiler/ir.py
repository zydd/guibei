from __future__ import annotations

import copy
import dataclasses
from collections import OrderedDict
from dataclasses import dataclass, field


from . import ast


@dataclass
class Node:
    ast_node: ast.Node | None

    def __iter__(self):
        return iter(self.__dataclass_fields__.keys())

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


@dataclass(init=False)
class Scope(Node):
    # Do not annotate parent scope to avoid infinite loops when traversing tree
    # parent: Scope | None
    vars: dict[str, Node] = field(default_factory=dict)
    types: dict[str, Type] = field(default_factory=dict)
    stmts: list[Node] = field(default_factory=list)

    def __init__(self, parent: Scope | None = None, stmts=None):
        super().__init__(None)
        self.parent = parent
        self.vars = dict()
        self.types = dict()
        self.stmts = stmts or list()

    def register_var(self, name: str, var: Node):
        assert not self.has_member(name)
        self.vars[name] = var

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

    def lookup_var(self, name: str) -> Node:
        if name in self.vars:
            return self.vars[name]
        elif self.parent:
            return self.parent.lookup_var(name)
        else:
            raise KeyError(f"Variable '{name}' not found")


@dataclass
class Untranslated(Node):
    def __repr__(self):
        return f"Untranslated({self.ast_node})"

    def translate(self, scope: Scope):
        type_name = type(self.ast_node).__name__
        ir_type = globals().get(type_name)
        if ir_type:
            return ir_type.translate(self.ast_node, scope)
        raise NotImplementedError


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


@dataclass(init=False)
class TypeDef(Type):
    super_: Type | None
    name: str
    scope: Scope

    def __init__(self, ast_node: ast.Node | None, super_: Type | None, name: str, scope: Scope):
        super().__init__(ast_node)
        self.super_ = super_
        self.name = name
        self.scope = scope
        self_ref = TypeRef(None, name, self)
        self.scope.register_type("Self", self_ref)
        # self.scope.register_type(name, self_ref)

    def add_method(self, name: str, method: Node):
        assert not self.scope.has_member(name)
        self.scope.register_var(name, method)


@dataclass
class UntranslatedType(Type):
    def __repr__(self):
        return f"UntranslatedType({self.ast_node})"

    def translate(self, scope: Scope) -> Type:
        type_name = type(self.ast_node).__name__
        ir_type = globals().get(type_name)
        if ir_type:
            return ir_type.translate(self.ast_node, scope)
        match self.ast_node:
            case ast.TypeIdentifier():
                type_ = scope.lookup_type(self.ast_node.name)
                return TypeRef(self.ast_node, self.ast_node.name, type_)
            case ast.MemberAccess(expr=ast.TypeIdentifier() as expr, attr=str()):
                type_ = scope.lookup_type(expr.name)
                assert isinstance(type_, TypeDef)
                member = type_.scope.types[self.ast_node.attr]
                assert isinstance(member, TypeDef)
                return TypeRef(self.ast_node, member.name, member)
        raise NotImplementedError(type_name)


@dataclass(init=False)
class EnumType(TypeDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def translate(node: ast.EnumType, scope: Scope):
        enum_type = EnumType(node, None, node.name, Scope(scope))
        for i, val in enumerate(node.values):
            enum_type.scope.register_type(val.name, EnumValueType.translate(enum_type, i, val))
        return enum_type

    def add_method(self, name: str, method: Node):
        if self.scope.has_member(name):
            # TODO: ensure all overloaded functions/methods are defined together
            assert name in self.scope.vars
            # Look up only in current scope
            match self.scope.vars[name]:
                case FunctionDef() as fn:
                    self.scope.vars[name] = OverloadedFunction(None, name, [fn, method])
                case OverloadedFunction() as overloads:
                    overloads.overloads.append(method)
                case _:
                    raise NotImplementedError
        else:
            self.scope.register_var(name, method)


@dataclass(kw_only=True)
class EnumValueType(TypeDef):
    discr: int
    field_types: list[Type]

    @staticmethod
    def translate(enum: EnumType, discr: int, node: ast.EnumValueType):
        assert isinstance(node, ast.EnumValueType)
        field_types: list = [UntranslatedType(t) for t in node.field_types]
        return EnumValueType(
            node, TypeRef(None, enum.name, enum), node.name, Scope(enum.scope), discr=discr, field_types=field_types
        )


@dataclass
class ArrayType(Type):
    element_type: Type

    @staticmethod
    def translate(node: ast.ArrayType, scope: Scope):
        return ArrayType(node, UntranslatedType(node.element_type).translate(scope))


@dataclass
class VoidType(Type):
    @staticmethod
    def translate(node: ast.VoidType, _scope):
        return VoidType(node)


@dataclass
class TypeRef(Type):
    name: str
    # Do not annotate type reference to avoid infinite loops when traversing tree
    # type_: Type

    def __init__(self, ast_node: ast.Node | None, name: str, type_: Type):
        super().__init__(ast_node)
        self.name = name
        self.type_ = type_

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
class VarDecl(Node):
    name: str
    type_: Type


@dataclass
class VarRef(Node):
    # Do not annotate type reference to avoid infinite loops when traversing tree
    # var: Node

    def __init__(self, ast_node: ast.Node | None, var: ArgDecl | VarDecl):
        super().__init__(ast_node)
        self.var = var

    def __repr__(self):
        return f"VarRef({self.var.name})"


@dataclass
class SetLocal(Node):
    var: VarRef
    expr: Node


@dataclass
class FunctionDef(Node):
    type_: FunctionType
    scope: Scope

    @staticmethod
    def translate(node: ast.FunctionDef, scope: Scope):
        func_type = FunctionType.translate(node.type_)
        body: list = [Untranslated(stmt) for stmt in node.body]
        return FunctionDef(node, func_type, Scope(scope, body))


@dataclass
class OverloadedFunction(Node):
    name: str
    overloads: list[Node]
