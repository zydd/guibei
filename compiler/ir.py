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
    #     return f"{self.__class__.__name__}({fields})"


@dataclass(init=False)
class Scope(Node):
    # Do not annotate parent scope to avoid infinite loops when traversing tree
    # parent: Scope | None
    # name: str
    attrs: OrderedDict[str, Node] = field(default_factory=OrderedDict)
    body: list[Node] = field(default_factory=list)
    func: FunctionRef | None = None

    def __init__(
        self,
        parent: Scope | None,
        name: str,
        body: list[Node] | None = None,
        func: FunctionRef | None = None,
        ast_node=None,
    ):
        super().__init__(ast_node)
        self.parent = parent
        self.root: Scope = parent.root if parent else self
        self.name: str = f"{parent.name}.{name}" if parent else name
        self.attrs = OrderedDict()
        self.body = body or list()
        self.func = func
        self.children_names: set[str] = set()
        self.name = parent.new_child_name(name) if parent else name

    def new_child_name(self, name):
        name = f"{self.name}.{name}"
        if name in self.children_names:
            for i in itertools.count(1):
                if f"{name}${i}" not in self.children_names:
                    name = f"{name}${i}"
                    break
        self.children_names.add(name)
        return name

    def add_method(self, name: str, var: Node):
        assert not self.has_member(name)
        self.attrs[name] = var

    def register_local(self, name: str, var: VarDecl):
        if name in self.attrs:
            # Shadow previously declared local var
            for i in itertools.count():
                if f"__local.{name}${i}" not in self.attrs:
                    shadowed_name = f"__local.{name}${i}"
                    shadowed_var = self.attrs[name]
                    if isinstance(shadowed_var, VarRef):
                        assert hasattr(shadowed_var.var, "name"), shadowed_var
                        shadowed_var.var.name = shadowed_name
                    else:
                        assert hasattr(shadowed_var, "name"), shadowed_var
                        shadowed_var.name = shadowed_name
                    self.attrs[shadowed_name] = shadowed_var
                    break

        if self.func:
            self.attrs[name] = var
            return var
        else:
            func_scope = self.current_func().func.scope

            local_name = f"{func_scope.name}.{name}"
            if local_name in func_scope.attrs:
                for i in itertools.count(1):
                    if f"{local_name}${i}" not in func_scope.attrs:
                        local_name = f"{local_name}${i}"
                        break

            var.name = local_name
            func_scope.attrs[local_name] = var
            self.attrs[name] = VarRef(None, var)
            return var

    def register_type(self, name: str, type_: Type):
        assert not self.has_member(name), name

        if isinstance(type_, TypeRef):
            self.attrs[name] = type_
        else:
            global_name = f"{self.name}.{name}"
            if global_name in self.root.attrs:
                for i in itertools.count(1):
                    if f"{global_name}${i}" not in self.root.attrs:
                        global_name = f"{global_name}${i}"
                        break

            if isinstance(type_, (TypeDef, TemplateDef)):
                type_.name = global_name

            # self.root.attrs[global_name] = type_
            self.attrs[name] = type_

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

    def current_func(self) -> FunctionRef:
        func = self.func
        while not func:
            assert self.parent is not None
            self = self.parent
            func = self.func
        return func


@dataclass
class Module(Node):
    asm: list[Node]
    scope: Scope
    id_count: int = 0

    def __init__(self, ast_node: ast.Node | None, scope: Scope):
        super().__init__(ast_node)
        self.asm = []
        self.scope = scope
        self.id_count = 0

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

        raise NotImplementedError(type_name)


@dataclass(init=False)
class TypeDef(Type):
    super_: Type | None
    name: str
    scope: Scope

    def __init__(self, ast_node: ast.Node | None, super_: Type | None, name: str, scope: Scope):
        super().__init__(ast_node)
        assert not isinstance(super_, TypeDef)
        self.super_ = super_
        self.name = name
        self.scope = scope
        self_ref = TypeRef(None, self)
        self.scope.register_type("Self", self_ref)
        self.scope.attrs["__asm_type"] = AsmType(None, f"${self.scope.name}")
        # self.scope.register_type(name, self_ref)

    def primitive(self):
        return self.super_.primitive() if self.super_ else self

    def has_base_class(self, cls: Type):
        current: Type | None = self
        while True:
            if current == cls:
                return True

            if isinstance(current, TypeDef):
                current = current.super_
                if isinstance(current, TypeRef):
                    current = current.type_
            else:
                return False

    def __eq__(self, value):
        if isinstance(value, TypeRef):
            value = value.type_
        if not isinstance(value, TypeDef):
            return False
        return self.name == value.name


@dataclass
class ArrayType(Type):
    element_type: Type


@dataclass
class TupleType(Type):
    field_types: list[Type]

    # @staticmethod
    # def translate(node: ast.TupleType, scope: Scope):
    #     return TupleType(node, None, [UntranslatedType(t) for t in node.field_types])


@dataclass
class NamedTupleType(TupleType):
    # field_names: list[str]

    def __init__(self, ast_node: ast.Node | None, field_types: list[Type], field_names: list[str]):
        super().__init__(ast_node, field_types)
        self.field_names = field_names


@dataclass
class VoidType(Type):
    @staticmethod
    def translate(node: ast.VoidType, _scope):
        return VoidType(node)

    def __eq__(self, value):
        return isinstance(value, VoidType)


@dataclass
class FunctionType(Type):
    args: list[ArgDecl]
    ret_type: Type

    @staticmethod
    def translate(node: ast.FunctionType):
        args = [ArgDecl(arg, arg.name, UntranslatedType(arg.type_)) for arg in node.args]
        ret_type = UntranslatedType(node.ret_type) if node.ret_type else UnknownType()
        return FunctionType(node, args, ret_type)


@dataclass
class EnumTypeBase(TupleType):
    name: str = "__enum"

    def __init__(self, scope):
        discr = scope.lookup_type("__enum_discr")
        assert isinstance(discr, TypeDef)
        discr = TypeRef(None, discr)
        super().__init__(None, [discr])

    def __eq__(self, value):
        return isinstance(value, EnumTypeBase)


@dataclass
class EnumType(TypeDef):
    count: int

    def __init__(self, ast_node: ast.Node | None, super_: Type, name: str, scope: Scope, count: int):
        super().__init__(ast_node, super_, name, scope)
        self.count = count

    @staticmethod
    def translate(node: ast.EnumType, scope: Scope):
        return EnumType(node, EnumTypeBase(scope), node.name, Scope(scope, node.name), len(node.values))

    # def add_method(self, name: str, method: Node):
    #     if self.scope.has_member(name):
    #         # TODO: ensure all overloaded functions/methods are defined together
    #         assert name in self.scope.attrs
    #         # Look up only in current scope
    #         match self.scope.attrs[name]:
    #             case FunctionDef() as fn:
    #                 self.scope.attrs[name] = OverloadedFunction(None, name, [fn, method])
    #             case OverloadedFunction() as overloads:
    #                 overloads.overloads.append(method)
    #             case _:
    #                 raise NotImplementedError
    #     else:
    #         self.scope.register_var(name, method)

    def primitive(self):
        return self


@dataclass(kw_only=True)
class EnumValueType(TypeDef):
    discr: int
    fields: TupleType

    @staticmethod
    def translate(enum: EnumType, discr: int, node: ast.EnumValueType):
        assert isinstance(node, ast.EnumValueType)
        assert isinstance(enum.super_, TupleType)
        field_types: list = [UntranslatedType(t) for t in node.fields.field_types] if node.fields else []
        fields = TupleType(None, enum.super_.field_types + field_types)

        return EnumValueType(
            node, TypeRef(None, enum), node.name, Scope(enum.scope, node.name), discr=discr, fields=fields
        )

    def primitive(self):
        return self


@dataclass
class AstType(Type):
    name: str


@dataclass
class UnknownType(Type):
    def __init__(self):
        super().__init__(None)


@dataclass
class SelfType(Type):
    ref: TemplateRef

    def __init__(self, template: TemplateDef):
        super().__init__(None)
        self.ref = TemplateRef(None, template)


@dataclass
class TemplateDef(Node):
    name: str
    super_: Type | None
    scope: Scope
    instances: dict[tuple[str, ...], TypeDef]
    args: list[TemplateArg]

    def __init__(
        self,
        ast_node: ast.Node | None,
        name: str,
        super_: Type | None,
        scope: Scope,
        instances: dict[tuple[str, ...], TypeDef],
        args: list[TemplateArg],
    ):
        super().__init__(ast_node)
        assert not isinstance(super_, TypeDef)
        self.name = name
        self.super_ = super_
        self.scope = scope
        self.instances = instances
        self.args = args
        for arg in args:
            self.scope.register_type(arg.name, TemplateArgRef(None, arg))

        self.scope.register_type("Self", SelfType(self))

    @staticmethod
    def translate(node: ast.TemplateDef, scope: Scope):
        template_scope = Scope(scope, node.name)
        args = [TemplateArg(arg, arg.name) for arg in node.args]
        template_type = TemplateDef(
            node, node.name, UntranslatedType(node.super_) if node.super_ else None, template_scope, {}, args
        )
        return template_type


@dataclass
class TemplateArg(Type):
    name: str

    def primitive(self):
        raise NotImplementedError


@dataclass
class TemplateInst(Type):
    template: TemplateRef
    args: list[Type]

    @staticmethod
    def translate(node: ast.TemplateInst, scope: Scope):
        template_def = scope.lookup(node.name.name)
        assert isinstance(template_def, TemplateDef)
        template = TemplateRef(None, template_def)
        args: list[Type] = [UntranslatedType(arg) for arg in node.args]
        return TemplateInst(node, template, args)


# ----------------------------------------------------------------------
# Expressions
# ----------------------------------------------------------------------


@dataclass(init=False)
class Expr(Node):
    type_: Type

    def __init__(self, ast_node, type_=None):
        super().__init__(ast_node)
        self.type_ = type_ or UnknownType()


@dataclass
class VoidExpr(Expr):
    def __init__(self, ast_node):
        super().__init__(ast_node, VoidType(None))

    @staticmethod
    def translate(node: ast.VoidExpr, _scope):
        return VoidExpr(node)

    def __eq__(self, value):
        return isinstance(value, VoidExpr)


@dataclass
class Call(Expr):
    callee: Node
    args: list[Node]

    def __init__(self, ast_node, callee, args):
        super().__init__(ast_node)
        self.callee = callee
        self.args = args

    @staticmethod
    def translate(node: ast.Call, _scope: Scope):
        callee = Untranslated(node.callee)
        if isinstance(node.arg, ast.TupleExpr):
            args = [Untranslated(arg) for arg in node.arg.field_values]
        else:
            args = [Untranslated(node.arg)]
        return Call(node, callee, args)


# @dataclass
# class BoundMethod(Expr):
#     instance: Node
#     method: Node


@dataclass
class GetAttr(Expr):
    obj: Node
    attr: str

    def __init__(self, ast_node, obj, attr):
        super().__init__(ast_node)
        self.obj = obj
        self.attr = attr

    @staticmethod
    def translate(node: ast.GetAttr, _scope: Scope):
        obj = Untranslated(node.obj)
        return GetAttr(node, obj, node.attr)


@dataclass
class GetItem(Expr):
    expr: Expr
    idx: Expr
    idx_type: TypeRef

    def __init__(self, ast_node, expr, idx, idx_type, type_):
        super().__init__(ast_node, type_)
        self.expr = expr
        self.idx = idx
        self.idx_type = idx_type


@dataclass
class GetTupleItem(Expr):
    expr: Expr
    idx: int

    def __init__(self, ast_node, expr, idx, type_=None):
        super().__init__(ast_node, type_)
        self.expr = expr
        self.idx = idx

    @staticmethod
    def translate(node: ast.GetTupleItem, _scope: Scope):
        return GetTupleItem(node, Untranslated(node.expr), node.idx)


@dataclass
class Asm(Expr):
    terms: WasmExpr

    def __init__(self, ast_node, terms, type_=None):
        super().__init__(ast_node, type_)
        self.terms = terms

    @staticmethod
    def translate(node: ast.Asm, _scope: Scope):
        terms = Untranslated(node.terms)
        return Asm(node, terms)


@dataclass
class IntLiteral(Expr):
    value: int

    def __init__(self, ast_node, value):
        super().__init__(ast_node, AstType(None, "__int"))
        self.value = value

    @staticmethod
    def translate(node: ast.IntLiteral, _scope: Scope):
        return IntLiteral(node, node.value)

    def __repr__(self):
        return f"IntLiteral({self.value})"


@dataclass
class StringLiteral(Expr):
    value: str
    temp_var: VarRef

    def __init__(self, ast_node, value, temp_var):
        super().__init__(ast_node, AstType(None, "__string_literal"))
        self.value = value
        self.temp_var = temp_var

    @staticmethod
    def translate(node: ast.StringLiteral, scope: Scope):
        temp_var = VarDecl(None, "__str", UnknownType())
        scope.register_local("__str", temp_var)
        return StringLiteral(node, node.value, VarRef(None, temp_var))

    def __repr__(self):
        return f"StringLiteral({self.value})"


@dataclass
class Placeholder(Expr):
    pass

    @staticmethod
    def translate(node: ast.Placeholder, _scope: Scope):
        return Placeholder(node, UnknownType())


@dataclass(init=False)
class WasmExpr(Node):
    terms: list[WasmExpr | str | int]

    def __init__(self, ast_node: ast.Node | None, terms):
        super().__init__(ast_node)
        self.terms = [WasmExpr(None, t) if isinstance(t, list) else t for t in terms]

    @staticmethod
    def translate(node: ast.WasmExpr, _scope: Scope) -> Node:
        terms: list = [Untranslated(term) if isinstance(term, ast.Node) else term for term in node.terms]
        return WasmExpr(node, terms)


@dataclass
class Block(Expr):
    name: str
    scope: Scope


# ----------------------------------------------------------------------
# References
# ----------------------------------------------------------------------

# Do not annotate referenced objects to avoid infinite loops when traversing tree


@dataclass
class FunctionRef(Expr):
    # function: FunctionDef

    def __init__(self, ast_node: ast.Node | None, func: FunctionDef):
        super().__init__(ast_node, TypeRef(None, func.type_))
        self.func = func

    def __deepcopy__(self, memo):
        return FunctionRef(self.ast_node, self.func)

    def __repr__(self):
        return f'FunctionRef("{self.func.name}")'


@dataclass
class MacroRef(Node):
    # macro: MacroDef

    def __init__(self, ast_node: ast.Node | None, macro: MacroDef):
        super().__init__(ast_node)
        self.macro = macro

    def __deepcopy__(self, memo):
        return MacroRef(self.ast_node, self.macro)

    def __repr__(self):
        return f'MacroRef("{self.macro.name}")'


@dataclass
class TypeRef(Type):
    # type_: Type

    def __init__(self, ast_node: ast.Node | None, type_: Type):
        super().__init__(ast_node)
        assert not isinstance(type_, TypeRef)
        self.type_ = type_

    def __repr__(self):
        return f'TypeRef("{getattr(self.type_, "name", "*" + str(type(self.type_).__name__))}")'

    def __eq__(self, value):
        value_type = value.type_ if isinstance(value, TypeRef) else value
        return self.type_ == value_type

    def __deepcopy__(self, memo):
        return TypeRef(self.ast_node, self.type_)

    def primitive(self):
        return self.type_.primitive()

    @property
    def name(self):
        return self.type_.name


@dataclass
class VarRef(Expr):
    # var: Node

    def __init__(self, ast_node: ast.Node | None, var: VarDecl):
        # super().__init__(ast_node, var.type_)
        self.ast_node = ast_node
        self.var = var

    def __deepcopy__(self, memo):
        return VarRef(self.ast_node, self.var)

    def __repr__(self):
        return f'VarRef("{self.var.name}")'

    @property  # type:ignore
    def type_(self):
        return self.var.type_

    @type_.setter
    def type_(self, value):
        self.var.type_ = value


@dataclass
class ArgRef(Expr):
    # arg: ArgDecl

    def __init__(self, ast_node: ast.Node | None, arg: ArgDecl):
        # super().__init__(ast_node, arg.type_)
        self.ast_node = ast_node
        self.arg = arg

    def __deepcopy__(self, memo):
        return ArgRef(self.ast_node, self.arg)

    def __repr__(self):
        return f"ArgRef({self.arg.name})"

    @property  # type:ignore
    def type_(self):
        return self.arg.type_

    @type_.setter
    def type_(self, value):
        self.arg.type_ = value


@dataclass
class TemplateRef(Type):
    # template: TemplateDef
    def __init__(self, ast_node: ast.Node | None, template: TemplateDef):
        super().__init__(ast_node)
        self.template = template

    def __deepcopy__(self, memo):
        return ArgRef(self.ast_node, self.arg)

    def __repr__(self):
        return f"TemplateRef({self.template.name})"


@dataclass
class TemplateArgRef(Type):
    def __init__(self, ast_node: ast.Node | None, arg: TemplateArg):
        super().__init__(ast_node)
        self.arg = arg

    def __deepcopy__(self, memo):
        return ArgRef(self.ast_node, self.arg)

    def __repr__(self):
        return f"TemplateArgRef({self.arg.name})"


# ----------------------------------------------------------------------
# Statements
# ----------------------------------------------------------------------

# TODO: Convert as much as possible into expressions


@dataclass
class FunctionDef(Node):
    name: str
    type_: FunctionType
    scope: Scope

    operators = {
        "-": "minus",
        ";": "semi",
        ":": "col",
        "!": "ex",
        "?": "qu",
        "@": "at",
        "*": "star",
        "/": "slash",
        "&": "and",
        "%": "perc",
        "`": "bt",
        "^": "hat",
        "+": "plus",
        "<": "lt",
        "=": "eq",
        ">": "gt",
        "|": "or",
        "~": "til",
    }

    @staticmethod
    def get_name(name):
        func_name = name
        if func_name.startswith("("):
            func_name = "__operator"
            for c in name[1:-1]:
                func_name += "$" + FunctionDef.operators[c]
        return func_name

    @staticmethod
    def translate(node: ast.FunctionDef, scope: Scope):
        func_type = FunctionType.translate(node.type_)
        body: list = [Untranslated(stmt) for stmt in node.body]
        func_name = FunctionDef.get_name(node.name)
        func = FunctionDef(node, f"{scope.name}.{func_name}", func_type, Scope(scope, node.name, body))
        func.scope.func = FunctionRef(None, func)
        return func


@dataclass
class MacroDef(Node):
    name: str
    func: FunctionDef

    @staticmethod
    def translate(node: ast.MacroDef, scope: Scope):
        # TODO: add the macro itself to the scope to allow recursion?
        return MacroDef(node, node.name, FunctionDef.translate(node.func, scope))


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
    func: FunctionRef
    expr: Node

    @staticmethod
    def translate(node: ast.FunctionReturn, scope: Scope):
        expr = Untranslated(node.expr) if node.expr is not None else VoidExpr(None)
        return FunctionReturn(node, scope.current_func(), expr)


@dataclass
class Break(Node):
    block_name: str
    expr: Expr

    def __init__(self, ast_node: ast.Node | None, block_name: str, expr: Expr):
        super().__init__(ast_node)
        self.block_name = block_name
        self.expr = expr


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
class MatchCase(Node):
    expr: Node
    scope: Scope


@dataclass
class MatchCaseEnum(Node):
    enum: Node
    args: list[Node]
    scope: Scope

    @staticmethod
    def from_case(case: MatchCase) -> MatchCaseEnum:
        if isinstance(case, MatchCaseEnum):
            assert isinstance(case.enum, TypeRef)
            assert isinstance(case.enum.type_, EnumValueType)
            case.args.insert(0, IntLiteral(None, case.enum.type_.discr))
            return case
        elif isinstance(case.expr, Call):
            assert isinstance(case.expr.callee, TypeRef)
            assert isinstance(case.expr.callee.primitive(), EnumValueType)
            return MatchCaseEnum(
                case.ast_node,
                case.expr.callee,
                [IntLiteral(None, case.expr.callee.primitive().discr)] + case.expr.args,
                case.scope,
            )
        else:
            assert isinstance(case.expr, TupleInst), case.expr
            return MatchCaseEnum(
                case.ast_node,
                case.expr.type_,
                [IntLiteral(None, case.expr.type_.primitive().discr)],
                case.scope,
            )


@dataclass
class Match(Node):
    match_expr: Node
    cases: list[MatchCase]
    scope: Scope

    @staticmethod
    def translate(node: ast.Match, scope: Scope):
        match_scope = Scope(scope, "__match")
        expr_var = VarDecl(None, "__match_expr", UnknownType())
        match_scope.register_local("__match_expr", expr_var)
        expr_assign = Assignment(None, VarRef(None, expr_var), Untranslated(node.expr))
        cases = [Match._translate_case(case, match_scope) for case in node.cases]
        return Match(node, expr_assign, cases, match_scope)

    @staticmethod
    def _translate_case(node: ast.MatchCase, scope: Scope):
        match node.expr:
            case ast.Call():
                expr = Untranslated(node.expr.callee)
                assert isinstance(node.expr.arg, ast.TupleExpr)
                args: list = [Untranslated(arg) for arg in node.expr.arg.field_values]
                statements: list = [Untranslated(stmt) for stmt in node.body]
                case_scope = Scope(scope, "__case", statements)
                # discriminant arg is added in MatchCaseEnum.from_case
                return MatchCaseEnum(node, expr, args, case_scope)

            case _:
                expr = Untranslated(node.expr)
                statements = [Untranslated(stmt) for stmt in node.body]
                case_scope = Scope(scope, "__case", statements)
                return MatchCase(node, expr, case_scope)


@dataclass
class MatchEnum(Node):
    match_expr: Node
    cases: list[MatchCaseEnum]
    scope: Scope


@dataclass
class Assignment(Node):
    lvalue: Node
    expr: Node

    @staticmethod
    def translate(node: ast.Assignment, _scope: Scope):
        lvalue = Untranslated(node.lvalue)
        expr = Untranslated(node.expr)
        return Assignment(node, lvalue, expr)


# Runtime


@dataclass
class AsmType(Node):
    name: str


@dataclass
class FunctionCall(Expr):
    func: FunctionRef
    args: list[Node]


@dataclass
class BoundMethod(Expr):
    func: FunctionRef
    obj: Expr


@dataclass
class SetItem(Node):
    expr: Expr
    idx: Expr
    idx_type: TypeRef
    value: Expr


@dataclass
class Drop(Node):
    expr: Expr

    def __init__(self, expr: Expr):
        super().__init__(None)
        self.expr = expr


@dataclass
class TupleInst(Expr):
    args: list[Expr]


@dataclass
class MacroInst(Expr):
    macro: MacroRef
    args: list[Node]

    def __init__(self, ast_node: ast.Node | None, type_: Type, macro: MacroRef, args: list[Node]):
        super().__init__(ast_node, type_)
        self.macro = macro
        self.args = args


@dataclass
class ReinterpretCast(Expr):
    expr: Expr


@dataclass
class Cast(Expr):
    expr: Expr
