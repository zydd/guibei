from __future__ import annotations

import itertools

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
    name: str
    attrs: OrderedDict[str, Node] = field(default_factory=OrderedDict)
    body: list[Node] = field(default_factory=list)
    func: FunctionRef | None = None

    def __init__(
        self, parent: Scope | None, name: str, body: list[Node] | None = None, func: FunctionRef | None = None
    ):
        super().__init__(None)
        self.parent = parent
        self.root: Scope = parent.root if parent else self
        self.name = f"{parent.name}.{name}" if parent else name
        self.attrs = OrderedDict()
        self.body = body or list()
        self.func = func

    def register_var(self, name: str, var: Node):
        assert not self.has_member(name)
        self.attrs[name] = var

    def register_local(self, name: str, var: ArgDecl | VarDecl):
        if name in self.attrs:
            # Shadow previously declared local var
            for i in itertools.count():
                if f"__local.{name}.{i}" not in self.attrs:
                    self.attrs[f"__local.{name}.{i}"] = self.attrs[name]
                    break

        if self.func:
            self.attrs[name] = var
        else:
            func_scope = self.parent
            while func_scope and not func_scope.func:
                func_scope = func_scope.parent
            if not func_scope:
                raise RuntimeError("Not in function scope")

            local_name = f"__local{self.name[len(func_scope.name):]}.{name}"
            for i in itertools.count():
                if f"{local_name}.{i}" not in func_scope.attrs:
                    local_name = f"{local_name}.{i}"
                    break

            var.name = local_name
            func_scope.attrs[local_name] = var
            self.attrs[name] = VarRef(None, var)

    def register_type(self, name: str, type_: Type):
        assert not self.has_member(name)

        if isinstance(type_, TypeRef):
            self.attrs[name] = type_
        else:
            global_name = f"__global{self.name[len(self.root.name):]}.{name}"
            for i in itertools.count():
                if f"{global_name}.{i}" not in self.root.attrs:
                    global_name = f"{global_name}.{i}"
                    break

            if isinstance(type_, TypeDef):
                type_.name = global_name
            self.root.attrs[global_name] = type_
            self.attrs[name] = TypeRef(None, global_name, type_)

    def has_member(self, name: str) -> bool:
        return name in self.attrs

    def lookup_type(self, name: str) -> Type:
        if name in self.attrs:
            res = self.attrs[name]
            assert isinstance(res, Type)
            if isinstance(res, TypeRef):
                res = res.type_
            return res
        elif self.parent:
            return self.parent.lookup_type(name)
        else:
            raise KeyError(f"Type '{name}' not found")

    def lookup(self, name: str) -> Node:
        if name in self.attrs:
            return self.attrs[name]
        elif self.parent:
            return self.parent.lookup(name)
        else:
            raise KeyError(f"Attribute '{name}' not found")


@dataclass
class Module(Node):
    scope: Scope
    asm: list[Node] = field(default_factory=list)
    id_count: int = 0

    def next_id(self):
        self.id_count += 1
        return self.id_count

    def add_asm(self, asm: Node):
        self.asm.append(asm)


@dataclass
class Untranslated(Node):
    def __repr__(self):
        return f"Untranslated({self.ast_node})"

    def translate(self, scope: Scope):
        type_name = type(self.ast_node).__name__
        ir_type = globals().get(type_name)
        if ir_type:
            return ir_type.translate(self.ast_node, scope)
        raise NotImplementedError(self)


# ----------------------------------------------------------------------
# Types
# ----------------------------------------------------------------------


@dataclass
class Type(Node):
    def primitive(self):
        return self


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
            case ast.GetAttr(obj=ast.TypeIdentifier() as expr, attr=str()):
                type_ = scope.lookup_type(expr.name)
                assert isinstance(type_, TypeDef)
                member = type_.scope.attrs[self.ast_node.attr]
                assert isinstance(member, TypeDef)
                return TypeRef(self.ast_node, member.name, member)
        raise NotImplementedError(type_name)


@dataclass(init=False)
class TypeDef(Type):
    super_: Type
    name: str
    scope: Scope

    def __init__(self, ast_node: ast.Node | None, super_: Type, name: str, scope: Scope):
        super().__init__(ast_node)
        assert not isinstance(super_, TypeDef)
        self.super_ = super_
        self.name = name
        self.scope = scope
        self_ref = TypeRef(None, name, self)
        self.scope.register_type("Self", self_ref)
        # self.scope.register_type(name, self_ref)

    def add_method(self, name: str, method: Node):
        assert not self.scope.has_member(name)
        self.scope.register_var(name, method)

    def primitive(self):
        return self.super_.primitive()


@dataclass
class ArrayType(Type):
    element_type: Type

    @staticmethod
    def translate(node: ast.ArrayType, scope: Scope):
        return ArrayType(node, UntranslatedType(node.element_type).translate(scope))


@dataclass
class TupleType(Type):
    fields: list[Type]

    @staticmethod
    def translate(node: ast.TupleType, scope: Scope):
        return TupleType(node, [UntranslatedType(t).translate(scope) for t in node.field_types])


@dataclass
class VoidType(Type):
    @staticmethod
    def translate(node: ast.VoidType, _scope):
        return VoidType(node)


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


@dataclass(init=False)
class EnumType(TypeDef):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def translate(node: ast.EnumType, scope: Scope):
        return EnumType(node, None, node.name, Scope(scope, node.name))

    def add_method(self, name: str, method: Node):
        if self.scope.has_member(name):
            # TODO: ensure all overloaded functions/methods are defined together
            assert name in self.scope.attrs
            # Look up only in current scope
            match self.scope.attrs[name]:
                case FunctionDef() as fn:
                    self.scope.attrs[name] = OverloadedFunction(None, name, [fn, method])
                case OverloadedFunction() as overloads:
                    overloads.overloads.append(method)
                case _:
                    raise NotImplementedError
        else:
            self.scope.register_var(name, method)

    def primitive(self):
        return self


@dataclass(kw_only=True)
class EnumValueType(TypeDef):
    discr: int
    field_types: list[Type]

    @staticmethod
    def translate(enum: EnumType, discr: int, node: ast.EnumValueType):
        assert isinstance(node, ast.EnumValueType)
        field_types: list = [UntranslatedType(t) for t in node.field_types]
        return EnumValueType(
            node,
            TypeRef(None, enum.name, enum),
            node.name,
            Scope(enum.scope, node.name),
            discr=discr,
            field_types=field_types,
        )


# ----------------------------------------------------------------------
# Expressions
# ----------------------------------------------------------------------


@dataclass(init=False)
class Expr(Node):
    # TODO: Implement __init__ for subtypes of Expr
    # type_: TypeRef | None = None
    pass


@dataclass
class Call(Expr):
    callee: Node
    args: list[Node]

    @staticmethod
    def translate(node: ast.Call, _scope: Scope):
        callee = Untranslated(node.callee)
        args: list = [Untranslated(arg) for arg in node.args]
        return Call(node, callee, args)


# @dataclass
# class BoundMethod(Expr):
#     instance: Node
#     method: Node


@dataclass
class GetAttr(Expr):
    obj: Node
    attr: str

    @staticmethod
    def translate(node: ast.GetAttr, _scope: Scope):
        obj = Untranslated(node.obj)
        return GetAttr(node, obj, node.attr)


@dataclass
class GetItem(Expr):
    expr: Node
    idx: Node

    @staticmethod
    def translate(node: ast.GetItem, _scope: Scope):
        expr = Untranslated(node.expr)
        idx = Untranslated(node.idx)
        return GetItem(node, expr, idx)


@dataclass
class Asm(Expr):
    terms: Node

    @staticmethod
    def translate(node: ast.Asm, _scope: Scope):
        terms = Untranslated(node.terms)
        return Asm(node, terms)


@dataclass
class IntLiteral(Expr):
    value: int

    @staticmethod
    def translate(node: ast.IntLiteral, _scope: Scope):
        return IntLiteral(node, node.value)

    def __repr__(self):
        return f"IntLiteral({self.value})"


@dataclass
class StringLiteral(Expr):
    value: str

    @staticmethod
    def translate(node: ast.StringLiteral, _scope: Scope):
        return StringLiteral(node, node.value)

    def __repr__(self):
        return f"StringLiteral({self.value})"


@dataclass(init=False)
class WasmExpr(Node):
    terms: list[WasmExpr | str | int]

    def __init__(self, ast_node: ast.Node | None, terms):
        self.ast_node = ast_node
        self.terms = [WasmExpr(None, t) if isinstance(t, list) else t for t in terms]

    @staticmethod
    def translate(node: ast.WasmExpr, _scope: Scope) -> Node:
        terms: list = [Untranslated(term) if isinstance(term, ast.Node) else term for term in node.terms]
        return WasmExpr(node, terms)


# ----------------------------------------------------------------------
# References
# ----------------------------------------------------------------------

# Do not annotate referenced objects to avoid infinite loops when traversing tree


@dataclass
class FunctionRef(Expr):
    name: str
    # function: FunctionDef

    def __init__(self, ast_node: ast.Node | None, name: str, function: FunctionDef):
        super().__init__(ast_node)
        self.name = name
        self.function = function

    def __repr__(self):
        return f"FunctionRef({self.name})"


@dataclass
class TypeRef(Type):
    name: str
    # type_: Type

    def __init__(self, ast_node: ast.Node | None, name: str, type_: Type):
        super().__init__(ast_node)
        assert not isinstance(type_, TypeRef)
        self.name = name
        self.type_ = type_

    def __repr__(self):
        return f"TypeRef({self.name})"

    def primitive(self):
        return self.type_.primitive()


@dataclass
class VarRef(Expr):
    # var: Node

    def __init__(self, ast_node: ast.Node | None, var: ArgDecl | VarDecl):
        super().__init__(ast_node)
        self.var = var

    def __repr__(self):
        return f"VarRef({self.var.name})"


# ----------------------------------------------------------------------
# Statements
# ----------------------------------------------------------------------

# TODO: Convert as much as possible into expressions


@dataclass
class FunctionDef(Node):
    type_: FunctionType
    scope: Scope

    @staticmethod
    def translate(node: ast.FunctionDef, scope: Scope):
        func_type = FunctionType.translate(node.type_)
        body: list = [Untranslated(stmt) for stmt in node.body]
        func = FunctionDef(node, func_type, Scope(scope, node.name, body))
        func.scope.func = FunctionRef(None, node.name, func)
        return func


@dataclass
class ArgDecl(Node):
    name: str
    type_: Type


@dataclass
class VarDecl(Node):
    name: str
    type_: Type


@dataclass
class SetLocal(Node):
    var: VarRef
    expr: Node


@dataclass
class OverloadedFunction(Node):
    name: str
    overloads: list[Node]


@dataclass
class FunctionReturn(Node):
    expr: Node

    @staticmethod
    def translate(node: ast.FunctionReturn, _scope: Scope):
        return FunctionReturn(node, Untranslated(node.expr))


@dataclass
class Loop(Node):
    pre_condition: Node
    scope: Scope
    post_condition: Node | None = None


@dataclass
class IfElse(Node):
    condition: Node
    scope_then: Scope
    scope_else: Scope

    @staticmethod
    def translate(node: ast.IfElse, scope: Scope):
        condition = Untranslated(node.condition)
        scope_then = Scope(scope, "__if", body=[Untranslated(stmt) for stmt in node.body_then])
        scope_else = Scope(scope, "__else", body=[Untranslated(stmt) for stmt in node.body_else])
        return IfElse(node, condition, scope_then, scope_else)


@dataclass
class Assignment(Node):
    lvalue: Node
    expr: Node

    @staticmethod
    def translate(node: ast.Assignment, _scope: Scope):
        lvalue = Untranslated(node.lvalue)
        expr = Untranslated(node.expr)
        return Assignment(node, lvalue, expr)
