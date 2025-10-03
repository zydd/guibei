import compiler.wast as wast


class TupleDef:
    def __init__(self, field_types):
        self.field_types = field_types

    def compile(self) -> list[wast.WasmExpr]:
        fields = []
        for  type_ in self.field_types:
            fields.append(wast.WasmExpr(["field",  *type_.compile()]))
        return [wast.WasmExpr(["struct", *fields])]

