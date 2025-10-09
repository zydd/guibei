from .wast import WasmExpr
from .ast import AstNode
from .fndef import FunctionDef, FunctionCall
from .typedef import NewType, TypeInstantiation


class Call(AstNode):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def annotate(self, context, expected_type):
        self.callee = self.callee.annotate(context, None)
        match self.callee:
            case FunctionDef():
                return FunctionCall(self.callee, self.args).annotate(context, expected_type)
            case _ if isinstance(self.callee, NewType):
                return TypeInstantiation(self.callee, self.args).annotate(context, expected_type)

        raise TypeError(f"Cannot call non-function '{self.callee}'")

    def __repr__(self):
        return f"{self.callee}{tuple(self.args)}"
