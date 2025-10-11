from .wast import Asm, WasmExpr
from .ast import AstNode

from compiler.typedef import NewType, VoidType
from compiler.statements import ReturnStatement


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


class FunctionType(NewType):
    def __init__(self, name, args, ret_type):
        super().__init__(name, None)
        self.args = args
        self.ret_type = ret_type

    def annotate(self, context, expected_type):
        self.args = [(arg_name, arg_type.annotate(context, None)) for arg_name, arg_type in self.args]

        if self.ret_type:
            self.ret_type = self.ret_type.annotate(context, None)

        return self

    def primitive(self):
        return self

    def declaration(self):
        decls = []
        for arg_name, arg_type in self.args:
            decls.append(WasmExpr(["param", f"${arg_name}", *arg_type.compile()]))

        if not isinstance(self.ret_type, VoidType):
            decls.append(WasmExpr(["result", *self.ret_type.compile()]))

        type_ = WasmExpr(["func", *decls])
        if self.name is not None:
            type_ = WasmExpr(["type", f"${self.name}", type_])
        return [type_]


class FunctionDef(AstNode):
    def __init__(self, name, args, ret_type, body):
        self.name = name
        self.type_ = FunctionType(f"__func_{name}_t", args, ret_type)
        self.body = body
        self.locals = {}

    def annotate(self, context, expected_type):
        context = context.new()
        context._current_function = self

        self.type_ = self.type_.annotate(context, expected_type)

        for arg_name, arg_type in self.type_.args:
            if arg_name == "self":
                arg_type.check_type(context.lookup_type("Self"))

            assert arg_name not in context.variables
            context.variables[arg_name] = VarDecl(arg_name, arg_type)

        for i, expr in enumerate(self.body[:-1]):
            if isinstance(expr, ReturnStatement):
                expr = expr.annotate(context, self.type_.ret_type)
            else:
                expr = expr.annotate(context, None)

            self.body[i] = expr
            assert expr is not None, self.body[i]

        if self.body:
            expr = self.body[-1]
            expr = expr.annotate(context, self.type_.ret_type)

            self.body[-1] = expr
            assert expr is not None, self.body[i]

        if hasattr(self, "annotations"):
            assert self.body == []
            context.register_import(
                WasmExpr(
                    [
                        "func",
                        f"${self.name}",
                        WasmExpr([self.annotations[0].callee, *self.annotations[0].args]),
                        WasmExpr(["type", f"${self.type_.name}"]),
                    ]
                )
            )

        return self

    def compile(self):
        if not self.body:
            return []

        decls = []
        for arg_name, arg_type in self.type_.args:
            decls.append(WasmExpr(["param", f"${arg_name}", *arg_type.compile()]))

        if not isinstance(self.type_.ret_type, VoidType):
            decls.append(WasmExpr(["result", *self.type_.ret_type.compile()]))

        for name, var in self.locals.items():
            decls.append(WasmExpr(["local", f"${name}", *var.var_type.compile()]))

        body = []
        for expr in self.body[:-1]:
            body.extend(expr.compile())

            if not isinstance(expr, Asm) and not isinstance(expr.type_, VoidType):
                body.append(WasmExpr(["drop"]))

        if self.body:
            body.extend(self.body[-1].compile())

            if (
                isinstance(self.type_.ret_type, VoidType)
                and not isinstance(self.body[-1], Asm)
                and not isinstance(self.body[-1].type_, VoidType)
            ):
                body.append(WasmExpr(["drop"]))

        return [WasmExpr(["func", f"${self.name}", WasmExpr(["type", f"${self.type_.name}"]), *decls, *body])]


class FunctionCall(AstNode):
    def __init__(self, func, args):
        self.func = func
        self.args = args
        self.type_ = func.type_.ret_type

    def annotate(self, context, expected_type):
        self.args = [
            arg_value.annotate(context, arg_type) for arg_value, (_, arg_type) in zip(self.args, self.func.type_.args)
        ]
        return self

    def compile(self):
        args = []
        for arg in self.args:
            args.extend(arg.compile())
        return [WasmExpr(["call", f"${self.func.name}", *args])]
