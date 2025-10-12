from .ast import AstNode
from .wast import WasmExpr


class TupleIndex(AstNode):
    def __init__(self, tuple_, idx):
        self.tuple_ = tuple_
        self.idx = idx
        self.type_ = None

    def annotate(self, context, expected_type):
        self.tuple_ = self.tuple_.annotate(context, None)
        self.type_ = self.tuple_.type_.primitive().field_types[self.idx]
        self.type_.check_type(expected_type)
        return self

    def compile(self):
        return [WasmExpr(["struct.get", f"${self.tuple_.type_.name}", str(self.idx), *self.tuple_.compile()])]
