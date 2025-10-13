from compiler.ast import AstNode
from compiler.fndef import FunctionDef
from compiler.typedef import NewType, TypeInstantiation
from compiler.wast import WasmExpr


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


class MemberAccess(AstNode):
    def __init__(self, expr, attr):
        self.expr = expr
        self.attr = attr

    def annotate(self, context, expected_type):
        self.expr = self.expr.annotate(context, None)

        if isinstance(self.expr, NewType):
            assert expected_type is None
            expr_type = self.expr
        else:
            expr_type = self.expr.type_

        type_ = expr_type
        method = None
        while type_ and not method:
            method = type_.methods.get(self.attr)
            type_ = type_.super_

        if not method:
            raise TypeError(f"Type '{expr_type.name}' has no method '{self.attr}'")

        match method:
            case FunctionDef():
                method.type_.ret_type.check_type(expected_type)
                if isinstance(self.expr, NewType):
                    return method
                else:
                    return BoundMethod(method, self.expr)
            case NewType():
                assert not expected_type
                return method
        raise NotImplementedError

    def compile(self):
        return [WasmExpr(["struct.get", f"${self.expr.type_.name}", str(self.attr), *self.expr.compile()])]


class FunctionCall(AstNode):
    def __init__(self, func, args):
        self.func = func
        self.args = args
        self.type_ = func.type_.ret_type

    def annotate(self, context, expected_type):
        self.args = [
            arg_value.annotate(context, arg_type.annotate(context, None))
            for arg_value, (_, arg_type) in zip(self.args, self.func.type_.args)
        ]
        return self

    def compile(self):
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [WasmExpr(["call", f"${self.func.name}", *args])]


class CastExpr(AstNode):
    def __init__(self, type_, expr):
        self.type_ = type_
        self.expr = expr

    def annotate(self, context, expected_type):
        # self.type_ = self.type_.annotate(context, None)
        # self.expr = self.type_.annotate(context, None)
        # TODO: only allow primitive type -> NewType instantiation
        return Call(self.type_, [self.expr]).annotate(context, expected_type)
