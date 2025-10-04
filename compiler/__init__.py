import typing

from .fndef import *
from .typedef import *
from .wast import *


class Context:
    def __init__(self, parent=None):
        self.parent = parent
        self.root = parent.root if parent else self

        self.variables: dict[str, VarDecl] = dict()
        self.types: dict[str, TypeDef] = dict()
        self.functions: dict[str, FunctionDef] = dict()

    def child(self):
        return Context(self)


class CompilePass:
    def __init__(self):
        self.wasm = []
        self.root_context = Context()

    def annotate(self, prog: list):
        for expr in prog:
            match expr:
                case FunctionDef():
                    self.root_context.functions[expr.name] = expr
                case TypeDef():
                    self.root_context.types[expr.name] = expr
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
