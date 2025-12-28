from __future__ import annotations

import itertools

from collections import OrderedDict
from dataclasses import dataclass, field


from . import ast


@dataclass
class Node:
    info: object

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
    #         f"{f.name}={getattr(self, f.name)}" for f in dataclasses.fields(self) if f.name != "info"
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
        info=None,
    ):
        super().__init__(info)
        self.parent = parent
        self.root: Scope = parent.root if parent else self
        self.module_scope: Scope | None = parent.module_scope if parent else None
        self.name: str = f"{parent.name}.{name}" if parent else name
        self.attrs = OrderedDict()
        self.body = body or list()
        self.func = func
        self.children_names: set[str] = set()
        self.name = parent.new_child_name(name) if parent else name

    def __deepcopy__(self, memo):
        import copy

        new_scope = Scope(
            self.parent,
            self.name,
            body=copy.deepcopy(self.body, memo),
            func=self.func,
            info=self.info,
        )
        new_scope.attrs = copy.deepcopy(self.attrs, memo)
        return new_scope

    def new_child_name(self, name):
        name = f"{self.name}.{name}"
        if name in self.children_names or name in self.attrs:
            for i in itertools.count(1):
                if f"{name}${i}" not in self.children_names:
                    name = f"{name}${i}"
                    break
        self.children_names.add(name)
        return name

    def add_method(self, name: str, method: Node, overload=False):
        if self.has_member(name):
            if overload:
                assert isinstance(method, (FunctionRef, MacroRef))
                cur = self.attrs[name]
                if not isinstance(cur, OverloadedFunction):
                    cur = OverloadedFunction(None, name, [cur])
                assert isinstance(cur, OverloadedFunction)
                cur.overloads.append(method)
                self.attrs[name] = cur
            else:
                raise RuntimeError(f"Method '{name}' already defined in '{self.name}'")
        else:
            self.attrs[name] = method

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

    def register_type(self, name: str, type_: Type | TemplateDef):
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

    def __init__(self, info, scope: Scope):
        super().__init__(info)
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
    ast_node: ast.Node

    def __init__(self, ast_node: ast.Node):
        super().__init__(ast_node.info)
        self.ast_node = ast_node

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
    sorting = 0

    def primitive(self):
        return self

    def has_base_class(self, _cls: Type):
        return False

    def get_attr(self, attr):
        raise KeyError(attr)

    def get_type_reference(self):
        type_ref = self.get_attr("__type_reference")
        match type_ref:
            case MacroDef():
                return type_ref.func.scope
            case Asm():
                return type_ref
            case _:
                raise NotImplementedError


@dataclass
class UntranslatedType(Type):
    ast_node: ast.Node

    def __init__(self, ast_node: ast.Node):
        super().__init__(None)
        self.ast_node = ast_node

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

    def __init__(self, info, super_: Type | None, name: str, scope: Scope):
        super().__init__(info)
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

    def get_attr(self, attr):
        if attr in self.scope.attrs:
            return self.scope.attrs[attr]
        if self.super_ is None:
            raise KeyError(attr)
        return self.super_.get_attr(attr)

    def __eq__(self, value):
        if isinstance(value, TypeRef):
            value = value.type_
        if not isinstance(value, TypeDef):
            return False
        return self.name == value.name

    def __deepcopy__(self, memo):
        raise RuntimeError

    def __copy__(self):
        raise RuntimeError


@dataclass
class IntegralType(Type):
    native_type: str
    array_packed: str
    array_get: str

    @staticmethod
    def translate(node: ast.IntegralType, _scope):
        return IntegralType(node.info, node.native_type, node.array_packed, node.array_get)

    def get_attr(self, attr):
        attrs = {"__type_reference": Asm(None, WasmExpr(None, [self.native_type]), BuiltinType("__type"))}
        return attrs[attr]


@dataclass
class NativeArrayType(Type):
    element_type: Type


@dataclass
class TupleType(Type):
    field_types: list[Type]

    # @staticmethod
    # def translate(node: ast.TupleType, scope: Scope):
    #     return TupleType(node.info, None, [UntranslatedType(t) for t in node.field_types])


@dataclass
class NamedTupleType(TupleType):
    # field_names: list[str]

    def __init__(self, info, field_types: list[Type], field_names: list[str]):
        super().__init__(info, field_types)
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
        args = [
            ArgDecl(arg.info, arg.name, UntranslatedType(arg.type_) if arg.type_ else UnknownType())
            for arg in node.args
        ]
        ret_type = UntranslatedType(node.ret_type) if node.ret_type else UnknownType()
        return FunctionType(node.info, args, ret_type)


@dataclass
class EnumIntType(TypeDef):
    def __init__(self, info, super_: Type | None, name: str, scope: Scope):
        super().__init__(info, super_, name, scope)


@dataclass
class EnumType(TypeDef):
    count: int
    discr_type: TypeRef

    def __init__(self, info, name: str, scope: Scope, count: int, discr_type: TypeRef):
        super().__init__(info, None, name, scope)
        self.count = count
        self.discr_type = discr_type

    def primitive(self):
        return self


@dataclass(kw_only=True)
class EnumValueType(TypeDef):
    discr: int
    discr_type: TypeRef
    field_types: list[Type]

    @staticmethod
    def translate(enum: EnumType, discr: int, discr_type: TypeRef, node: ast.EnumValueType):
        field_types: list[Type] = [UntranslatedType(t) for t in node.fields.field_types] if node.fields else []

        return EnumValueType(
            node.info,
            TypeRef(None, enum),
            node.name,
            Scope(enum.scope, node.name),
            discr=discr,
            discr_type=discr_type,
            field_types=field_types,
        )

    def primitive(self):
        return self


@dataclass
class BuiltinType(Type):
    name: str

    def __init__(self, name):
        super().__init__(None)
        self.name = name

    def __eq__(self, value):
        return isinstance(value, BuiltinType) and self.name == value.name


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
        info,
        name: str,
        super_: Type | None,
        scope: Scope,
        instances: dict[tuple[str, ...], TypeDef],
        args: list[TemplateArg],
    ):
        super().__init__(info)
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
            node.info, node.name, UntranslatedType(node.super_) if node.super_ else None, template_scope, {}, args
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
        return TemplateInst(node.info, template, args)


# ----------------------------------------------------------------------
# Expressions
# ----------------------------------------------------------------------


@dataclass(init=False)
class Expr(Node):
    type_: Type

    def __init__(self, info, type_=None):
        super().__init__(info)
        self.type_ = type_ or UnknownType()


@dataclass
class VoidExpr(Expr):
    def __init__(self, info):
        super().__init__(info, VoidType(None))

    @staticmethod
    def translate(node: ast.VoidExpr, _scope):
        return VoidExpr(node)

    def __eq__(self, value):
        return isinstance(value, VoidExpr)


@dataclass
class Call(Expr):
    callee: Node
    arg: Node

    def __init__(self, info, callee, arg, type_=None):
        super().__init__(info, type_)
        self.callee = callee
        self.arg = arg

    @staticmethod
    def translate(node: ast.Call, _scope: Scope):
        return Call(node.info, Untranslated(node.callee), Untranslated(node.arg))


@dataclass
class OpCall(Expr):
    callee: Node
    args: list[Node]


@dataclass
class GetAttr(Expr):
    expr: Node
    attr: str

    def __init__(self, info, obj, attr):
        super().__init__(info)
        self.expr = obj
        self.attr = attr

    @staticmethod
    def translate(node: ast.GetAttr, _scope: Scope):
        obj = Untranslated(node.obj)
        return GetAttr(node.info, obj, node.attr)


@dataclass
class GetItem(Expr):
    expr: Expr
    idx: Expr


@dataclass
class GetNativeArrayItem(Expr):
    expr: Expr
    idx: Expr


@dataclass
class GetEnumItem(Expr):
    expr: Expr
    idx: int


@dataclass
class GetTupleItem(Expr):
    expr: Expr
    idx: int


@dataclass
class SetTupleItem(Expr):
    expr: Expr
    idx: int
    value: Expr

    def __init__(self, info, expr, idx, value):
        super().__init__(info)
        self.expr = expr
        self.idx = idx
        self.value = value


@dataclass
class Asm(Expr):
    terms: WasmExpr

    def __init__(self, info, terms, type_=None):
        super().__init__(info, type_)
        self.terms = terms

    @staticmethod
    def translate(node: ast.Asm, _scope: Scope):
        terms = Untranslated(node.terms)
        return Asm(node.info, terms)


@dataclass
class IntLiteral(Expr):
    value: int

    def __init__(self, info, value):
        super().__init__(info, BuiltinType("__int"))
        self.value = value

    @staticmethod
    def translate(node: ast.IntLiteral, _scope: Scope):
        return IntLiteral(node.info, node.value)

    def __repr__(self):
        return f"IntLiteral({self.value})"


@dataclass
class EnumDiscr(Expr):
    value: int

    def __init__(self, value):
        super().__init__(None, BuiltinType("__enum_discr"))
        self.value = value


@dataclass
class StringLiteral(Expr):
    value: str

    def __init__(self, info, value):
        super().__init__(info, BuiltinType("__str"))
        self.value = value

    @staticmethod
    def translate(node: ast.StringLiteral, scope: Scope):
        return StringLiteral(node.info, node.value)

    def __repr__(self):
        return f"StringLiteral({repr(self.value)})"


@dataclass
class Placeholder(Expr):
    pass

    @staticmethod
    def translate(node: ast.Placeholder, _scope: Scope):
        return Placeholder(node.info, UnknownType())


@dataclass(init=False)
class WasmExpr(Node):
    terms: list[WasmExpr | str | int]

    def __init__(self, info, terms):
        super().__init__(info)
        self.terms = [WasmExpr(None, t) if isinstance(t, list) else t for t in terms]

    @staticmethod
    def translate(node: ast.WasmExpr, _scope: Scope) -> Node:
        terms: list = [Untranslated(term) if isinstance(term, ast.Node) else term for term in node.terms]
        return WasmExpr(node.info, terms)


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

    def __init__(self, info, func: FunctionDef):
        super().__init__(info, TypeRef(None, func.type_))
        self.func = func

    def __deepcopy__(self, memo):
        return FunctionRef(self.info, self.func)

    def __repr__(self):
        return f'FunctionRef("{self.func.name}")'

    def ref(self, info=None):
        return self


@dataclass
class ConstRef(Expr):
    # const: ConstDecl

    def __init__(self, info, const: ConstDecl):
        # super().__init__(info, None)
        self.info = info
        self.const = const

    def __deepcopy__(self, memo):
        return ConstRef(self.info, self.const)

    def __repr__(self):
        return f'ConstRef("{self.const.name}")'

    @property  # type:ignore[misc]
    def type_(self):
        return self.const.expr.type_


@dataclass
class MacroRef(Node):
    # macro: MacroDef

    def __init__(self, info, macro: MacroDef):
        super().__init__(info)
        self.macro = macro

    def __deepcopy__(self, memo):
        return MacroRef(self.info, self.macro)

    def __repr__(self):
        return f'MacroRef("{self.macro.name}")'

    def ref(self, info=None):
        return self


@dataclass
class TypeRef(Type):
    # type_: Type

    def __init__(self, info, type_: Type):
        super().__init__(info)
        assert not isinstance(type_, (TypeRef, TemplateArgRef))
        self.type_ = type_

    def __repr__(self):
        return f'TypeRef("{getattr(self.type_, "name", "*" + str(type(self.type_).__name__))}")'

    def __eq__(self, value):
        value_type = value.type_ if isinstance(value, TypeRef) else value
        return self.type_ == value_type

    def __deepcopy__(self, memo):
        return TypeRef(self.info, self.type_)

    def primitive(self):
        return self.type_.primitive()

    @property
    def name(self):
        return self.type_.name

    def has_base_class(self, cls: Type):
        return self.type_.has_base_class(cls)

    def get_attr(self, attr):
        return self.type_.get_attr(attr)


@dataclass
class VarRef(Expr):
    # var: Node
    # TODO: only store index for args and variable references

    def __init__(self, info, var: VarDecl):
        # super().__init__(info, var.type_)
        self.info = info
        self.var = var

    def __deepcopy__(self, memo):
        return VarRef(self.info, self.var)

    def __repr__(self):
        return f'VarRef("{self.var.name}")'

    @property
    def name(self):
        return self.var.name

    @property  # type:ignore[misc]
    def type_(self):
        return self.var.type_

    @type_.setter
    def type_(self, value):
        self.var.type_ = value


@dataclass
class ArgRef(Expr):
    # arg: ArgDecl
    # TODO: only store index for args and variable references

    def __init__(self, info, arg: ArgDecl):
        # super().__init__(info, arg.type_)
        self.info = info
        self.var = arg

    def __deepcopy__(self, memo):
        return ArgRef(self.info, self.var)

    def __repr__(self):
        return f"ArgRef({self.var.name})"

    @property
    def name(self):
        return self.var.name

    @property  # type:ignore
    def type_(self):
        return self.var.type_

    @type_.setter
    def type_(self, value):
        self.var.type_ = value


@dataclass
class TemplateRef(Type):
    # template: TemplateDef
    def __init__(self, info, template: TemplateDef):
        super().__init__(info)
        self.template = template

    def __deepcopy__(self, memo):
        return TemplateRef(self.info, self.template)

    def __repr__(self):
        return f"TemplateRef({self.template.name})"


@dataclass
class TemplateArgRef(Type):
    def __init__(self, info, arg: TemplateArg):
        super().__init__(info)
        self.arg = arg

    def __deepcopy__(self, memo):
        return TemplateArgRef(self.info, self.arg)

    def __repr__(self):
        return f"TemplateArgRef({self.arg.name})"

    @property
    def name(self):
        return self.arg.name


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
        elif func_name == "[]":
            func_name = "$index"
        elif func_name == "[]=":
            func_name = "$set_index"
        return func_name

    @staticmethod
    def translate(node: ast.FunctionDef, scope: Scope):
        func_type = FunctionType.translate(node.type_)
        body: list = [Untranslated(stmt) for stmt in node.body]
        func_name = FunctionDef.get_name(node.name)
        func = FunctionDef(node.info, f"{scope.name}.{func_name}", func_type, Scope(scope, func_name, body))
        func.scope.func = FunctionRef(None, func)

        if hasattr(node, "annotations"):
            func.annotations = node.annotations  # type:ignore[attr-defined]

        return func

    def ref(self, info=None):
        return FunctionRef(info, self)


@dataclass
class MacroDef(Node):
    name: str
    func: FunctionDef

    @staticmethod
    def translate(node: ast.MacroDef, scope: Scope):
        # TODO: add the macro itself to the scope to allow recursion?
        return MacroDef(node.info, node.name, FunctionDef.translate(node.func, scope))

    @property  # type:ignore[misc]
    def type_(self):
        return self.func.type_

    def ref(self, info=None):
        return MacroRef(info, self)


@dataclass
class AstMacroDef(Node):
    name: str
    func: FunctionDef

    @staticmethod
    def translate(node: ast.AstMacroDef, scope: Scope):
        return AstMacroDef(node.info, node.name, FunctionDef.translate(node.func, scope))


@dataclass
class ArgDecl(Node):
    name: str
    type_: Type


@dataclass
class VarDecl(Node):
    name: str
    type_: Type


@dataclass
class ConstDecl(Node):
    name: str
    expr: Expr

    @staticmethod
    def translate(node: ast.ConstDecl, scope: Scope):
        # TODO: UntranslatedExpr
        return ConstDecl(node.info, node.name, Untranslated(node.init))  # type:ignore[arg-type]


@dataclass
class SetLocal(Node):
    var: VarRef | ArgRef
    expr: Node


@dataclass
class OverloadedFunction(Node):
    name: str
    overloads: list[Node]

    def ref(self, info=None):
        return self


@dataclass
class FunctionReturn(Node):
    func: FunctionRef
    expr: Node

    @staticmethod
    def translate(node: ast.FunctionReturn, scope: Scope):
        expr = Untranslated(node.expr) if node.expr is not None else VoidExpr(None)
        return FunctionReturn(node.info, scope.current_func(), expr)


@dataclass
class Break(Node):
    block_name: str
    expr: Expr

    def __init__(self, info, block_name: str, expr: Expr):
        super().__init__(info)
        self.block_name = block_name
        self.expr = expr


@dataclass
class TemplateFor(Node):
    bindings: list[ArgDecl]
    iterable: Expr
    body: Scope

    @staticmethod
    def translate(node: ast.TemplateFor, scope: Scope):
        bindings = [ArgDecl(binding.info, binding.name, UnknownType()) for binding in node.bindings]
        iterable = Untranslated(node.iterable)
        body_scope = Scope(scope, "__for", body=[Untranslated(stmt) for stmt in node.body])
        for arg in bindings:
            body_scope.add_method(arg.name, ArgRef(arg.info, arg))
        return TemplateFor(node.info, bindings, iterable, body_scope)  # type:ignore[arg-type]


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
        return IfElse(node.info, condition, scope_then, scope_else)


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
            case.args.insert(0, EnumDiscr(case.enum.type_.discr))
            return case
        elif isinstance(case.expr, Call):
            assert isinstance(case.expr.callee, TypeRef)
            assert isinstance(case.expr.callee.primitive(), EnumValueType)
            assert isinstance(case.expr.arg, TupleExpr)
            args: list = [EnumDiscr(case.expr.callee.primitive().discr)] + case.expr.arg.args
            return MatchCaseEnum(
                case.info,
                case.expr.callee,
                args,
                case.scope,
            )
        else:
            assert isinstance(case.expr, EnumInst), case.expr
            return MatchCaseEnum(
                case.info,
                case.expr.type_,
                [EnumDiscr(case.expr.discr)],
                case.scope,
            )


@dataclass
class Match(Node):
    match_expr: SetLocal
    cases: list[MatchCase]
    scope: Scope

    @staticmethod
    def translate(node: ast.Match, scope: Scope):
        match_scope = Scope(scope, "__match")
        expr_var = VarDecl(None, "__match_expr", UnknownType())
        match_scope.register_local("__match_expr", expr_var)
        expr_assign = SetLocal(None, VarRef(None, expr_var), Untranslated(node.expr))
        cases = [Match._translate_case(case, match_scope) for case in node.cases]
        return Match(node.info, expr_assign, cases, match_scope)

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
                return MatchCaseEnum(node.info, expr, args, case_scope)

            case ast.IntLiteral():
                statements = [Untranslated(stmt) for stmt in node.body]
                case_scope = Scope(scope, "__case", statements)
                return MatchIntCase(node.info, node.expr.value, case_scope)

            case _:
                expr = Untranslated(node.expr)
                statements = [Untranslated(stmt) for stmt in node.body]
                case_scope = Scope(scope, "__case", statements)
                return MatchCase(node.info, expr, case_scope)


@dataclass
class MatchEnum(Node):
    match_expr: SetLocal
    cases: list[MatchCaseEnum]
    scope: Scope


@dataclass
class MatchIntCase(Node):
    value: int
    scope: Scope


@dataclass
class MatchInt(Node):
    match_expr: SetLocal
    cases: list[MatchIntCase]
    scope: Scope


@dataclass
class Assignment(Node):
    lvalue: Node
    expr: Node

    @staticmethod
    def translate(node: ast.Assignment, _scope: Scope):
        lvalue = Untranslated(node.lvalue)
        expr = Untranslated(node.expr)
        return Assignment(node.info, lvalue, expr)


# Runtime


@dataclass
class Builtin(Node):
    name: str

    def __init__(self, name: str):
        super().__init__(None)
        self.name = name


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
    lvalue: Expr
    idx: Expr
    value: Expr


@dataclass
class SetNativeArrayItem(Node):
    lvalue: Expr
    idx: Expr
    value: Expr


@dataclass
class Drop(Node):
    expr: Expr

    def __init__(self, expr: Expr):
        super().__init__(None)
        self.expr = expr


@dataclass
class TupleExpr(Expr):
    args: list[Expr]

    @staticmethod
    def translate(node: ast.TupleExpr, _scope: Scope):
        args: list = [Untranslated(arg) for arg in node.field_values]
        return TupleExpr(node.info, UnknownType(), args)


@dataclass
class TupleInst(Expr):
    args: list[Expr]


@dataclass
class EnumInst(Expr):
    discr: int
    args: list[Expr]


@dataclass
class EnumInt(Expr):
    discr: int


@dataclass
class MacroInst(Expr):
    macro: MacroRef
    args: list[Node]


@dataclass
class ImplicitCast(Expr):
    macro: MacroRef
    expr: Expr


@dataclass
class ExplicitCast(Expr):
    macro: MacroRef
    expr: Expr


@dataclass
class ReinterpretCast(Expr):
    expr: Expr


@dataclass
class Cast(Expr):
    expr: Expr


@dataclass
class RefCast(Expr):
    expr: Expr
