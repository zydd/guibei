from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Node:
    info = None

    def __iter__(self):
        return iter(self.__dict__.keys())

    def __getitem__(self, i):
        return getattr(self, i)

    def __setitem__(self, i, value):
        return setattr(self, i, value)

    def __repr__(self):
        return f"ast.{self.__class__.__name__}"


# ----------------------------------------------------------------------
# Types
# ----------------------------------------------------------------------


@dataclass
class Type(Node):
    pass


@dataclass
class TupleType(Type):
    field_types: list[Type]


@dataclass
class ArrayType(Type):
    element_type: Type


@dataclass
class NativeArrayType(Type):
    element_type: Type


@dataclass
class IntegralType(Type):
    native_type: str
    array_packed: str
    array_get: str


@dataclass
class VoidType(Type):
    pass


@dataclass
class VoidExpr(Node):
    pass


@dataclass
class FunctionType(Type):
    args: list[ArgDecl]
    ret_type: Type | None


@dataclass
class TypeDef(Type):
    name: str
    super_: Type | None


@dataclass
class TemplateDef(Node):
    name: str
    args: list[Identifier]
    super_: Type | None


@dataclass
class TemplateInst(Type):
    name: TypeIdentifier
    args: list[Type]


@dataclass
class TypeIdentifier(Type):
    name: str

    def __repr__(self):
        return f"TypeIdentifier({self.name})"


@dataclass
class EnumType(Type):
    name: str
    values: list[EnumValueType]


@dataclass
class EnumValueType(Type):
    name: str
    fields: TupleType | None


# ----------------------------------------------------------------------
# Expressions
# ----------------------------------------------------------------------


@dataclass
class GetItem(Node):
    expr: Node
    idx: Node


@dataclass
class NamedTupleElement(Node):
    name: str
    value: Node


@dataclass
class TupleExpr(Node):
    field_values: list[Node]


@dataclass
class IntLiteral(Node):
    value: int


@dataclass
class StringLiteral(Node):
    value: str


@dataclass
class Identifier(Node):
    name: str

    def __repr__(self):
        return f"Identifier({self.name})"


@dataclass
class Asm(Node):
    terms: WasmExpr


@dataclass
class WasmExpr(Node):
    terms: list[WasmExpr]


@dataclass
class Call(Node):
    callee: Node
    arg: Node


@dataclass
class AstMacroInst(Node):
    name: str
    arg: TupleExpr


@dataclass
class BinOp(Node):
    op: str
    lhs: Node
    rhs: Node


@dataclass
class UnaryL(Node):
    op: str
    arg: Node


@dataclass
class UnaryR(Node):
    op: str
    arg: Node


@dataclass
class GetAttr(Node):
    obj: Node
    attr: str


# ----------------------------------------------------------------------
# Statements
# ----------------------------------------------------------------------


@dataclass
class Module(Node):
    stmts: list[Node]

    def __init__(self, stmts: list[Node]):
        self.stmts = stmts


@dataclass
class FunctionDef(Node):
    name: str
    type_: FunctionType
    body: list[Node]


@dataclass
class AstMacroDef(Node):
    name: str
    func: FunctionDef


@dataclass
class MacroDef(Node):
    name: str
    func: FunctionDef


@dataclass
class TypeImpl(Node):
    type_: str
    methods: list[Node]


@dataclass
class TemplateTypeImpl(Node):
    args: list[Type]
    type_: TypeIdentifier | TemplateInst
    methods: list[Node]


@dataclass
class VarDecl(Node):
    name: str
    type_: Type | None
    init: Node


@dataclass
class ConstDecl(Node):
    name: str
    type_: Type | None
    init: Node


@dataclass
class ArgDecl(Node):
    name: str
    type_: Type | None


@dataclass
class IfElse(Node):
    condition: Node
    body_then: list[Node]
    body_else: list[Node]


@dataclass
class While(Node):
    condition: Node
    body: list[Node]


@dataclass
class MatchCase(Node):
    expr: Node
    body: list[Node]


@dataclass
class Match(Node):
    expr: Node
    cases: list[MatchCase]


@dataclass
class FunctionReturn(Node):
    expr: Node | None


@dataclass
class Assignment(Node):
    lvalue: Node
    expr: Node


@dataclass
class Placeholder(Node):
    pass
