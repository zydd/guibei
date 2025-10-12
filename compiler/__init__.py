import typing

from .fndef import *
from .typedef import *
from .wast import *
from .enum import Enum
from .context import Context


class CompilePass:
    def __init__(self):
        self.wasm = []
        self.root_context = Context()

    def annotate(self, prog: list):
        impl_blocks = []
        root_types = []
        root_functions = []

        for expr in prog:
            match expr:
                case _ if isinstance(expr, NewType):
                    self.root_context.register_type(expr)
                case FunctionDef():
                    self.root_context.register_func(expr)
                case TypeImpl():
                    impl_blocks.append(expr)

        root_types = list(self.root_context.types.items())
        root_functions = list(self.root_context.functions.items())

        for impl in impl_blocks:
            impl.register_methods(self.root_context)

        for name, type_ in root_types:
            self.root_context.types[name] = type_.annotate(self.root_context, None)

        for name, func in root_functions:
            self.root_context.functions[name].type_ = self.root_context.functions[name].type_.annotate(
                self.root_context, None
            )

        for name, func in root_functions:
            self.root_context.functions[name] = func.annotate(self.root_context, None)

        for expr in prog:
            match expr:
                case Asm():
                    expr.annotate(self.root_context, None)
                    self.wasm.extend(expr.compile())

    def compile(self, prog: list):
        self.annotate(prog)

        for type_ in self.root_context.types.values():
            self.wasm.extend(type_.declaration())

        for func in self.root_context.functions.values():
            self.wasm.extend(func.declaration())

    def write(self, out: typing.BinaryIO):
        out.write(b"(module\n")

        for w in self.root_context.imports:
            out.write(w.repr_indented(1).encode())
            out.write(b"\n")

        for w in self.wasm:
            out.write(w.repr_indented(1).encode())
            out.write(b"\n")

        out.write(b")\n")
        out.flush()
