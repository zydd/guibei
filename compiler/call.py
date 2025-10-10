from .wast import WasmExpr
from .ast import AstNode
from .fndef import FunctionDef, FunctionCall
from .typedef import NewType, TypeInstantiation


class Call(AstNode):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def annotate(self, context, expected_type):
        self.callee = self.callee.annotate(context, None)
        match self.callee:
            case FunctionDef():
                return FunctionCall(self.callee, self.args).annotate(context, expected_type)
            case BoundMethod():
                if self.callee.func.type_.args and self.callee.func.type_.args[0][0] == "self":
                    self.args = [self.callee.obj] + self.args
                return FunctionCall(self.callee.func, self.args).annotate(context, expected_type)
            case _ if isinstance(self.callee, NewType):
                return TypeInstantiation(self.callee, self.args).annotate(context, expected_type)

        raise TypeError(f"Cannot call non-function '{self.callee}'")

    def __repr__(self):
        return f"{self.callee}{tuple(self.args)}"


class BoundMethod(AstNode):
    def __init__(self, func, obj):
        self.func: FunctionDef = func
        self.obj = obj

    def annotate(self, context, expected_type):
        raise NotImplementedError

    def compile(self):
        raise NotImplementedError


class MethodAccess(AstNode):
    def __init__(self, expr, attr):
        self.expr = expr
        self.attr = attr
        self.type_ = None

    def annotate(self, context, expected_type):
        self.expr = self.expr.annotate(context, expected_type)
        self.type_ = self.expr.type_
        method = None
        type_ = self.type_
        while type_ and not method:
            method = type_.methods.get(self.attr)
            type_ = type_.super_
        if not method:
            raise TypeError(f"Type '{self.type_.name}' has no method '{self.attr}'")
        return BoundMethod(method, self.expr)

    def compile(self):
        return [WasmExpr(["struct.get", f"${self.expr.type_.name}", str(self.attr), *self.expr.compile()])]

