from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict

_ast_repr = False


@dataclass(repr=_ast_repr)
class Node:
    def __iter__(self):
        return iter(self.__dict__.keys())

    def __getitem__(self, i):
        return getattr(self, i)

    def __setitem__(self, i, value):
        return setattr(self, i, value)

    def __repr__(self):
        return f"ast.{self.__class__.__name__}"


@dataclass(repr=_ast_repr)
class Type(Node):
    pass


@dataclass(repr=_ast_repr)
class TypeDef(Node):
    name: str
    super_: Type


@dataclass(repr=_ast_repr)
class TupleType(Type):
    field_types: list[Type]


@dataclass(repr=_ast_repr)
class ArrayType(Type):
    element_type: Type


@dataclass(repr=_ast_repr)
class NativeType(Type):
    args: list[str]


@dataclass(repr=_ast_repr)
class VoidType(Type):
    pass


@dataclass(repr=_ast_repr)
class TypeIdentifier(Node):
    name: str

    def __repr__(self):
        return f"TypeIdentifier({self.name})"


@dataclass(repr=_ast_repr)
class GetItem(Node):
    expr: Node
    idx: Node


@dataclass(repr=_ast_repr)
class GetTupleItem(Node):
    expr: Node
    idx: int


@dataclass(repr=_ast_repr)
class TypeImpl(Node):
    type_name: str
    methods: list[Node]


@dataclass(repr=_ast_repr)
class IfElse(Node):
    condition: Node
    body_then: list[Node]
    body_else: list[Node]


@dataclass(repr=_ast_repr)
class While(Node):
    condition: Node
    body: list[Node]


@dataclass(repr=_ast_repr)
class FunctionReturn(Node):
    expr: Node


@dataclass(repr=_ast_repr)
class Assignment(Node):
    lvalue: Node
    expr: Node


@dataclass(repr=_ast_repr)
class IntLiteral(Node):
    value: int


@dataclass(repr=_ast_repr)
class StringLiteral(Node):
    value: str


@dataclass(repr=_ast_repr)
class Identifier(Node):
    name: str

    def __repr__(self):
        return f"Identifier({self.name})"


@dataclass(repr=_ast_repr)
class EnumValueType(TupleType):
    name: str


@dataclass(repr=_ast_repr)
class EnumType(Type):
    name: str
    values: list[EnumValueType]


@dataclass(repr=_ast_repr)
class Asm(Node):
    terms: WasmExpr


@dataclass(repr=_ast_repr)
class WasmExpr(Node):
    terms: list[WasmExpr]


@dataclass(repr=_ast_repr)
class VarDecl(Node):
    name: str
    type_: Type
    init: Node


@dataclass(repr=_ast_repr)
class ArgDecl(Node):
    name: str
    type_: Type


@dataclass(repr=_ast_repr)
class FunctionType(Type):
    args: list[ArgDecl]
    ret_type: Type


@dataclass(repr=_ast_repr)
class FunctionDef(Node):
    name: str
    type_: FunctionType
    body: list[Node]


@dataclass(repr=_ast_repr)
class Call(Node):
    callee: Node
    args: list[Node]


@dataclass(repr=_ast_repr)
class GetAttr(Node):
    obj: Node
    attr: str


@dataclass(repr=_ast_repr)
class Module(Node):
    stmts: list[Node]

    def __init__(self, stmts: list[Node]):
        self.stmts = stmts
