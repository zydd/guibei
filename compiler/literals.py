from compiler.ast import AstNode


class IntLiteral(AstNode):
    def __init__(self, value: int):
        self.value = value
        self.type_ = None

    def annotate(self, context, expected_type):
        self.type_ = expected_type
        return self

    def compile(self):
        return self.type_.primitive().instantiate([self.value])

    def __repr__(self):
        return repr(self.value)


class StringLiteral(AstNode):
    def __init__(self, value: str):
        self.value = value

    def annotate(self, context, expected_type):
        raise NotImplementedError

    def compile(self):
        raise NotImplementedError

    def __repr__(self):
        return self.value
