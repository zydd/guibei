from compiler.ast import AstNode
from compiler.wast import WasmExpr
from compiler.fndef import VarDecl


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
        self.value_str = value
        self.value = value.encode().decode("unicode_escape").encode()
        self.addr = None
        self.type_ = None
        self.temp_var_name = None

    def annotate(self, context, expected_type):
        self.addr = context.add_data(self.value)
        self.type_ = expected_type
        self.temp_var_name = f"__local_{self.next_id()}"
        context.register_variable(VarDecl(self.temp_var_name, self.type_))
        return self

    def compile(self):
        return [
            WasmExpr(
                [
                    f"local.tee ${self.temp_var_name}",
                    [f"array.new_default ${self.type_.name}", f"(i32.const {len(self.value)})"],
                ]
            ),
            *(
                WasmExpr(
                    [
                        f"array.set ${self.type_.name} (local.get ${self.temp_var_name}) (i32.const {i}) (i32.const {byte})"
                    ]
                )
                for i, byte in enumerate(self.value)
            ),
        ]

    def __repr__(self):
        return f'"{self.value_str}"'
