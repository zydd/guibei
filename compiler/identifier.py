import compiler.wast as wast


class Identifier:
    def __init__(self, name: str):
        self.name = name

    def compile(self) -> list[wast.WasmExpr]:
        return [wast.WasmExpr(["local.get", f"${self.name}"])]
