from .wast import WasmExpr
from .ast import AstNode


class VarDecl(AstNode):
    def __init__(self, name, type_, init, mutable=False):
        self.name = name
        self.type_ = type_
        self.init = init
        self.mutable = mutable

    def annotate(self, context):
        if self.init:
            self.init = self.init.annotate(context)
        context.register_variable(self)
        return self

    def compile(self):
        res = []
        if self.init:
            res.extend([WasmExpr(["local.set", f"${self.name}", *self.init.compile()])])
        return res


class FunctionDef(AstNode):
    def __init__(self, name, args, ret_type, body):
        self.name = name
        self.args = args
        self.ret_type = ret_type
        self.body = body
        self.locals = []

    def annotate(self, context):
        context = context.new()

        self.args = [(name, type_.annotate(context)) for name, type_ in self.args]

        if self.ret_type:
            self.ret_type = self.ret_type.annotate(context)

        for i, expr in enumerate(self.body):
            if isinstance(expr, VarDecl):
                self.locals.append((expr.name, expr.type_.annotate(context)))

            self.body[i] = expr.annotate(context)
            assert self.body[i] is not None, expr

        return self

    def compile(self):
        decls = []
        for name, type_ in self.args:
            decls.append(WasmExpr(["param", f"${name}", *type_.compile()]))

        if self.ret_type:
            decls.append(WasmExpr(["result", *self.ret_type.compile()]))

        for name, type_ in self.locals:
            decls.append(WasmExpr(["local", f"${name}", *type_.compile()]))

        body = []
        for expr in self.body:
            body.extend(expr.compile())

        return [WasmExpr(["func", f"${self.name}", *decls, *body])]


class FunctionCall:
    def __init__(self, func, args):
        self.func = func
        self.args = args

    def compile(self):
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [WasmExpr(["call", f"${self.func.name}", *args])]

