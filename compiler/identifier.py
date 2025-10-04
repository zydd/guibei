from compiler.ast import AstNode
from compiler.wast import WasmExpr


class Identifier(AstNode):
    def __init__(self, name: str):
        self.name = name

    def annotate(self, context):
        return self

    def compile(self):
        return [WasmExpr(["local.get", f"${self.name}"])]
