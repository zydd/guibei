import typing

from .fndef import *
from .typedef import *
from .wast import *
from .context import Context


class CompilePass:
    def __init__(self):
        self.wasm = []
        self.root_context = Context()

    def annotate(self, prog: list):
        for expr in prog:
            match expr:
                case FunctionDef():
                    self.root_context.register_func(expr)
                case TypeDef():
                    self.root_context.register_type(expr)
                case Asm():
                    self.wasm.extend(expr.compile())

        for name, type_ in self.root_context.types.items():
            self.root_context.types[name] = type_.annotate(self.root_context)

        for name, func in self.root_context.functions.items():
            self.root_context.functions[name] = func.annotate(self.root_context)

    def compile(self, prog: list):
        self.annotate(prog)

        for type_ in self.root_context.types.values():
            self.wasm.extend(type_.compile())

        for func in self.root_context.functions.values():
            self.wasm.extend(func.compile())

    def write(self, out: typing.BinaryIO):
        out.write(b"(module\n")

        for w in self.wasm:
            out.write(w.repr_indented(1).encode())
            out.write(b"\n")

        out.write(b")\n")
        out.flush()
