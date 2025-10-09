from compiler.ast import AstNode
from compiler.enum import EnumConst
from compiler.fndef import VarDecl, FunctionDef
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
        val = context.lookup(self.name)
        match val:
            case VarDecl():
                self.type_ = val.var_type
                return self
            case FunctionDef():
                self.type_ = val.type_
                return val
            case _ if isinstance(val, NewType):
                return val
            case EnumConst():
                return val
        raise NotImplementedError(self)

    def compile(self):
        return [WasmExpr(["local.get", f"${self.name}"])]

    def __repr__(self):
        return self.name