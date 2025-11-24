struct TokenState: (line: usize, column_begin: usize, column_end: usize, spaced: bool)

enum Token:
    Name(TokenState, str)
    String(TokenState, str)
    Int(TokenState, str)
    Symbol(TokenState, str)


type Line: (line: usize, indent: usize, comment: str, tokens: Token[])

