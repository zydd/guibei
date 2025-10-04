from compiler.ast import AstNode
from compiler.wast import WasmExpr


class Identifier(AstNode):
    def __init__(self, name: str):
        self.name = name
        self.type_ = None

    def annotate(self, context, expected_type):
        var = context.lookup(self.name)
        self.type_ = var.type_
        return self

    def compile(self):
        return [WasmExpr(["local.get", f"${self.name}"])]
