from .wast import WasmExpr
from .ast import AstNode
from .fndef import FunctionDef, FunctionCall
from .typedef import TypeDef, TypeInstantiation


class Call(AstNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def annotate(self, context, expected_type):
        callee = context.lookup(self.name)
        match callee:
            case FunctionDef():
                return FunctionCall(callee, self.args).annotate(context, expected_type)
            case TypeDef():
                return TypeInstantiation(callee, self.args).annotate(context, expected_type)

        raise TypeError(f"Cannot call non-function '{self.name}'")
