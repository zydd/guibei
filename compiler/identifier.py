from compiler.ast import AstNode
from compiler.typedef import NewType
from compiler.wast import WasmExpr


operator_characters = "-~`!@$%^&*+=|;:',<.>/?"


class Identifier(AstNode):
    def __init__(self, name: str):
        for i, c in enumerate(operator_characters):
            name = name.replace(c, f"${i}")

        self.name = name
        self.type_ = None

    def annotate(self, context, expected_type):
        if expected_type:
            return context.lookup_var(self.name)
        else:
            return context.lookup(self.name)

    def compile(self):
        return [WasmExpr(["local.get", f"${self.name}"])]

    def __repr__(self):
        return f"Id({self.name})"
