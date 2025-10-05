from compiler.ast import AstNode
from compiler.wast import WasmExpr

from compiler.fndef import VarDecl, FunctionDef
from compiler.typedef import TypeDef


class Identifier(AstNode):
    def __init__(self, name: str):
        self.name = name
        self.type_ = None

    def annotate(self, context, expected_type):
        val = context.lookup(self.name)
        match val:
            case VarDecl():
                self.type_ = val.type_
                return self
            case FunctionDef():
                self.type_ = val.type_
                return val
            case TypeDef():
                return val
            case _:
                raise NotImplementedError

    def compile(self):
        return [WasmExpr(["local.get", f"${self.name}"])]
