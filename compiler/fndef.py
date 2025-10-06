from .wast import WasmExpr
from .ast import AstNode


class VarDecl(AstNode):
    def __init__(self, name, type_, init=None, mutable=False):
        self.name = name
        self.type_ = type_
        self.init = init
        self.mutable = mutable

    def annotate(self, context, expected_type):
        self.type_ = self.type_.annotate(context, None)
        if self.init:
            self.init = self.init.annotate(context, self.type_)
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

        for arg in self.type_.args:
            context.register_variable(arg)

        for i, expr in enumerate(self.body):
            if isinstance(expr, VarDecl):
                self.locals.append((expr.name, expr.type_.annotate(context, None)))

            self.body[i] = expr.annotate(context, None)
            assert self.body[i] is not None, expr

        return self

    def compile(self):
        decls = []
        for arg in self.type_.args:
            decls.append(WasmExpr(["param", f"${arg.name}", *arg.type_.compile()]))

        if self.type_.ret_type:
            decls.append(WasmExpr(["result", *self.type_.ret_type.compile()]))

        for name, type_ in self.locals:
            decls.append(WasmExpr(["local", f"${name}", *type_.compile()]))

        body = []
        for expr in self.body:
            body.extend(expr.compile())

        return [WasmExpr(["func", f"${self.name}", *decls, *body])]


class FunctionCall(AstNode):
    def __init__(self, func, args):
        self.func = func
        self.args = args
        self.type_ = func.type_.ret_type

    def annotate(self, context, expected_type):
        self.args = [arg_value.annotate(context, arg_decl.type_) for arg_value, arg_decl in zip(self.args, self.func.type_.args)]
        return self

    def compile(self):
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [WasmExpr(["call", f"${self.func.name}", *args])]