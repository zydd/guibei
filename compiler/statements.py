from compiler.ast import AstNode
from compiler.typedef import NativeType, VoidType, ArrayIndex
from compiler.wast import WasmExpr
from compiler.identifier import Identifier


class IfStatement(AstNode):
    def __init__(self, condition, body_then, body_else):
        self.condition = condition
        self.body_then = body_then
        self.body_else = body_else
        self.type_ = VoidType()

    def annotate(self, context, expected_type):
        self.condition = self.condition.annotate(context, NativeType("i32"))
        self.body_then = [expr.annotate(context, None) for expr in self.body_then]
        self.body_else = [expr.annotate(context, None) for expr in self.body_else]
        return self

    def compile(self):
        body_then = []
        body_else = []

        for stmt in self.body_then:
            body_then.extend(stmt.compile())

        for stmt in self.body_else:
            body_else.extend(stmt.compile())

        res = [
            "if",
            *self.condition.compile(),
            [
                "then",
                *body_then,
            ],
        ]

        if self.body_else:
            res.append(["else", *body_else])

        return [WasmExpr(res)]


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
                    [
                        "loop",
                        f"$while_loop_{id}",
                        [
                            "br_if",
                            f"$while_block_{id}",
                            ["i32.eqz", *self.condition.compile()],
                        ],
                        *body,
                        ["br", f"$while_loop_{id}"],
                    ],
                ]
            )
        ]


class ReturnStatement(AstNode):
    def __init__(self, expr):
        self.expr = expr
        self.type_ = VoidType()

    def annotate(self, context, expected_type):
        # self.type_.check_type(expected_type)
        self.expr = self.expr.annotate(context, context.current_function().type_.ret_type)
        return self

    def compile(self):
        return [WasmExpr(["return", *self.expr.compile()])]


class Assignment(AstNode):
    def __init__(self, lvalue, expr):
        self.lvalue = lvalue
        self.expr = expr
        self.type_ = VoidType()

    def annotate(self, context, expected_type):
        self.lvalue = self.lvalue.annotate(context, None)
        self.expr = self.expr.annotate(context, self.lvalue.type_)
        if self.lvalue.type_ and self.expr.type_:
            self.lvalue.type_.check_type(self.expr.type_)
        return self

    def compile(self):
        return self.lvalue.assign(self.expr.compile())
