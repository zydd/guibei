import compiler.wast as wast


class VarDecl:
    def __init__(self, name, type_, init, mutable=False):
        self.name = name
        self.type_ = type_
        self.init = init
        self.mutable = mutable

    def compile(self) -> list[wast.WasmExpr]:
        res = [wast.WasmExpr(["local", f"${self.name}", *self.type_.compile()])]
        if self.init:
            res.extend([*self.init.compile(), wast.WasmExpr(["local.set", f"${self.name}"])])
        return res


class FunctionDef:
    def __init__(self, name, args, ret_type, body):
        self.name = name
        self.args = args
        self.ret_type = ret_type
        self.body = body

    def compile(self) -> list[wast.WasmExpr]:
        args = []
        for name, type_ in self.args:
            args.append(wast.WasmExpr(["param", f"${name}", *type_.compile()]))

        ret_type = []
        if self.ret_type:
            ret_type.append(wast.WasmExpr(["result", *self.ret_type.compile()]))

        body = []
        for expr in self.body:
            body.extend(expr.compile())

        return [wast.WasmExpr(["func", f"${self.name}", *args, *ret_type, *body])]


class FunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def compile(self) -> list[wast.WasmExpr]:
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [wast.WasmExpr(["call", f"${self.name}", *args])]
