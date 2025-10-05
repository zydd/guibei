from compiler.ast import AstNode


class IntLiteral(AstNode):
    def __init__(self, value: int):
        self.value = value
        self.native_type = None

    def annotate(self, context, expected_type):
        self.native_type = expected_type.root_type()
        return self

    def compile(self):
        return self.native_type.compile_literal(self.value)

    def __repr__(self):
        return repr(self.value)