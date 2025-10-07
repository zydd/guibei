from compiler.ast import AstNode
from compiler.typedef import NativeType
from compiler.wast import WasmExpr


class WhileStatement(AstNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def annotate(self, context, expected_type):
        self.condition = self.condition.annotate(context, NativeType("i32"))
        self.body = [expr.annotate(context, None) for expr in self.body]
        return self

    def compile(self):
        body = []
        for stmt in self.body:
            body.extend(stmt.compile())
        id = AstNode.next_id()
        return [WasmExpr(["block", f"$while_block_{id}",
            WasmExpr(["loop", f"$while_loop_{id}",
                WasmExpr(["br_if", f"$while_block_{id}",
                    WasmExpr(["i32.eqz",
                        *self.condition.compile()
                    ]),
                ]),

                *body,
                WasmExpr(["br", f"$while_loop_{id}"])
            ])
        ])]

class ReturnStatement(AstNode):
    def __init__(self, expr):
        self.expr = expr

    def annotate(self, context, expected_type):
        self.expr = self.expr.annotate(context, None)
        return self

    def compile(self):
        return [WasmExpr(["return", *self.expr.compile()])]
