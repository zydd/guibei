import compiler.wast as wast


class IntLiteral:
    def __init__(self, value: int):
        self.value = value

    def compile(self) -> list[wast.WasmExpr]:
        return [wast.WasmExpr(["i32.const", str(self.value)])]
