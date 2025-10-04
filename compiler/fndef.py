import compiler.wast as wast


class VarDecl:
    def __init__(self, name, type_, init, mutable=False):
        self.name = name
        self.type_ = type_
        self.init = init
        self.mutable = mutable

    def compile(self) -> list[wast.WasmExpr]:
        res = []
        if self.init:
            res.extend([*self.init.compile(), wast.WasmExpr(["local.set", f"${self.name}"])])
        return res


class FunctionDef:
    def __init__(self, name, args, ret_type, body):
        self.name = name
        self.args = args
        self.ret_type = ret_type
        self.body = body
        self.locals = []

    def annotate(self, context):
        for expr in self.body:
            if isinstance(expr, VarDecl):
                self.locals.append((expr.name, expr.type_))

        return self

    def compile(self) -> list[wast.WasmExpr]:
        decls = []
        for name, type_ in self.args:
            decls.append(wast.WasmExpr(["param", f"${name}", *type_.compile()]))

        if self.ret_type:
            decls.append(wast.WasmExpr(["result", *self.ret_type.compile()]))

        for name, type_ in self.locals:
            decls.append(wast.WasmExpr(["local", f"${name}", *type_.compile()]))

        body = []
        for expr in self.body:
            body.extend(expr.compile())

        return [wast.WasmExpr(["func", f"${self.name}", *decls, *body])]


class FunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def compile(self) -> list[wast.WasmExpr]:
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [wast.WasmExpr(["call", f"${self.name}", *args])]
