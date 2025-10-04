from .wast import WasmExpr
from .ast import AstNode


class VarDecl(AstNode):
    def __init__(self, name, type_, init, mutable=False):
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
    def __init__(self, name, arg_names, arg_types, ret_type):
        self.name = name
        self.arg_names = arg_names
        self.arg_types = arg_types
        self.ret_type = ret_type

    def annotate(self, context, expected_type):
        context = context.new()

        self.arg_types = [arg_type.annotate(context, None) for arg_type in self.arg_types]

        if self.ret_type:
            self.ret_type = self.ret_type.annotate(context, None)

        return self

    def declaration(self):
        return []


class FunctionDef(AstNode):
    def __init__(self, name, arg_names, arg_types, ret_type, body):
        self.name = name
        self.func_type = FunctionType(f"__func_t_{name}", arg_names, arg_types, ret_type)
        self.body = body
        self.locals = []

    def annotate(self, context, expected_type):
        context = context.new()

        for i, expr in enumerate(self.body):
            if isinstance(expr, VarDecl):
                self.locals.append((expr.name, expr.type_.annotate(context, None)))

            self.body[i] = expr.annotate(context, None)
            assert self.body[i] is not None, expr

        return self

    def compile(self):
        decls = []
        for name, type_ in zip(self.func_type.arg_names, self.func_type.arg_types):
            decls.append(WasmExpr(["param", f"${name}", *type_.compile()]))

        if self.func_type.ret_type:
            decls.append(WasmExpr(["result", *self.func_type.ret_type.compile()]))

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

    def annotate(self, context, expected_type):
        self.args = [arg.annotate(context, arg_type) for arg, arg_type in zip(self.args, self.func.func_type.arg_types)]
        return self

    def compile(self):
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [WasmExpr(["call", f"${self.func.name}", *args])]