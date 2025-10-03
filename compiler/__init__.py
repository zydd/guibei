import typing


class CompilePass:
    def __init__(self):
        self.wasm = []

    def compile(self, prog: list):
        for expr in prog:
            wasm = expr.compile()
            self.wasm.extend(wasm)

    def write(self, out: typing.BinaryIO):
        out.write(b"(module\n")

        for w in self.wasm:
            out.write(w.repr_indented(1).encode())
            out.write(b"\n")

        out.write(b")\n")
        out.flush()
