from .ast import AstNode
from .wast import WasmExpr


class TupleDecl(AstNode):
    def __init__(self, field_types):
        self.field_types = field_types

    def annotate(self, context, expected_type):
        self.field_types = [type_.annotate(context, None) for type_ in self.field_types]
        return self

    def declaration(self):
        fields = []
        for type_ in self.field_types:
            fields.append(WasmExpr(["field", *type_.compile()]))
        return [WasmExpr(["struct", *fields])]


class TupleIndex(AstNode):
    def __init__(self, tuple_, idx):
        self.tuple_ = tuple_
        self.idx = idx

    def annotate(self, context, expected_type):
        self.tuple_ = self.tuple_.annotate(context, expected_type)
        return self

    def compile(self):
        return [WasmExpr(["struct.get", f"${self.tuple_.type_.name}", str(self.idx), *self.tuple_.compile()])]
