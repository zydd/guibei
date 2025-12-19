# TODO:
# - Canonical names
# - Argument/variable indexing
# - Disallow implicit conversion from tuple to named tuple
# - Allow template instances as template arguments
# - Allow explicit casting between integral types


type TokenState: (line: usize, column_begin: usize, column_end: usize, spaced: bool)

enum Token:
    Name(TokenState, str)
    String(TokenState, str)
    Int(TokenState, str)
    Symbol(TokenState, str)


type Line: (line: usize, indent: usize, comment: str, tokens: [Token])



func main() -> ():
    match u8 48:
        case 48: bytes.print("zero\n")
        case 49: bytes.print("one\n")
        case 50: bytes.print("two\n")
        case 51: bytes.print("three\n")
        case 52: bytes.print("four\n")
        case 53: bytes.print("five\n")

    bytes.print("👨‍👩‍👧‍👦\n")
    bytes.print("🔤\n")
