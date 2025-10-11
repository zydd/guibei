from compiler.ast import AstNode
from compiler.typedef import NativeType, VoidType
from compiler.wast import WasmExpr


class WhileStatement(AstNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body
        self.type_ = VoidType()

    def annotate(self, context, expected_type):
        self.condition = self.condition.annotate(context, NativeType("i32"))
        self.body = [expr.annotate(context, None) for expr in self.body]
        return self

    def compile(self):
        body = []
        for stmt in self.body:
            body.extend(stmt.compile())
        id = AstNode.next_id()
        return [
            WasmExpr(
                [
                    "block",
                    f"$while_block_{id}",
                    WasmExpr(
                        [
                            "loop",
                            f"$while_loop_{id}",
                            WasmExpr(
                                [
                                    "br_if",
                                    f"$while_block_{id}",
                                    WasmExpr(["i32.eqz", *self.condition.compile()]),
                                ]
                            ),
                            *body,
                            WasmExpr(["br", f"$while_loop_{id}"]),
                        ]
                    ),
                ]
            )
        ]


class ReturnStatement(AstNode):
    def __init__(self, expr):
        self.expr = expr
        self.type_ = VoidType()

    def annotate(self, context, expected_type):
        self.expr = self.expr.annotate(context, expected_type)
        return self

    def compile(self):
        return [WasmExpr(["return", *self.expr.compile()])]


class Assignment(AstNode):
    def __init__(self, var, expr):
        self.var = var
        self.expr = expr

    def annotate(self, context, expected_type):
        self.var = self.var.annotate(context, None)
        self.expr = self.expr.annotate(context, self.var.type_)
        if self.var.type_ and self.expr.type_:
            self.var.type_.check_type(self.expr.type_)
        return self

    def compile(self):
        return [WasmExpr(["local.set", f"${self.var.name}", *self.expr.compile()])]
