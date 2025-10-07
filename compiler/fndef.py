from .wast import WasmExpr
from .ast import AstNode

from compiler.typedef import VoidType


class VarDecl(AstNode):
    def __init__(self, name, var_type, init=None, mutable=False):
        self.name = name
        self.var_type = var_type
        self.type_ = VoidType()
        self.init = init
        self.mutable = mutable

    def annotate(self, context, expected_type):
        self.var_type = self.var_type.annotate(context, None)
        if self.init:
            self.init = self.init.annotate(context, self.var_type)
        context.register_variable(self)
        return self

    def compile(self):
        res = []
        if self.init:
            res.extend([WasmExpr(["local.set", f"${self.name}", *self.init.compile()])])
        return res


class FunctionType(AstNode):
    def __init__(self, name, args, ret_type):
        self.name = name
        self.args = [VarDecl(arg_name, arg_type) for arg_name, arg_type in args]
        self.ret_type = ret_type

    def annotate(self, context, expected_type):
        context = context.new()
        self.args = [arg.annotate(context, None) for arg in self.args]

        if self.ret_type:
            self.ret_type = self.ret_type.annotate(context, None)

        return self

    def declaration(self):
        return []


class FunctionDef(AstNode):
    def __init__(self, name, args, ret_type, body):
        self.name = name
        self.type_ = FunctionType(f"__func_t_{name}", args, ret_type)
        self.body = body
        self.locals = []

    def annotate(self, context, expected_type):
        context = context.new()

        for i in range(len(self.type_.args)):
            self.type_.args[i] = self.type_.args[i].annotate(context, None)

        for i, expr in enumerate(self.body):
            if isinstance(expr, VarDecl):
                self.locals.append((expr.name, expr.var_type.annotate(context, None)))

            self.body[i] = expr.annotate(context, None)
            assert self.body[i] is not None, expr

        return self

    def compile(self):
        decls = []
        for arg in self.type_.args:
            decls.append(WasmExpr(["param", f"${arg.name}", *arg.var_type.compile()]))

        if not isinstance(self.type_.ret_type, VoidType):
            decls.append(WasmExpr(["result", *self.type_.ret_type.compile()]))

        for name, type_ in self.locals:
            decls.append(WasmExpr(["local", f"${name}", *type_.compile()]))

        body = []
        for expr in self.body[:-1]:
            body.extend(expr.compile())
            assert expr.type_ is not None
            if not isinstance(expr.type_, VoidType):
                body.append(WasmExpr(["drop"]))

        body.extend(self.body[-1].compile())

        return [WasmExpr(["func", f"${self.name}", *decls, *body])]


class FunctionCall(AstNode):
    def __init__(self, func, args):
        self.func = func
        self.args = args
        self.type_ = func.type_.ret_type

    def annotate(self, context, expected_type):
        self.args = [arg_value.annotate(context, arg_decl.var_type) for arg_value, arg_decl in zip(self.args, self.func.type_.args)]
        return self

    def compile(self):
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [WasmExpr(["call", f"${self.func.name}", *args])]
