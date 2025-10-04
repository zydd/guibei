from compiler.ast import AstNode
from compiler.wast import WasmExpr


class IntLiteral(AstNode):
    def __init__(self, value: int):
        self.value = value

    def annotate(self, context):
        return self

    def compile(self):
        return [WasmExpr(["i32.const", str(self.value)])]
