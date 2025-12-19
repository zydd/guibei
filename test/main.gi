# TODO:
# - Canonical names
# - Argument/variable indexing
# - Disallow implicit conversion from tuple to named tuple
# - Allow template instances as template arguments
# - Allow explicit casting between integral types: u32(char"c")


type TokenState: (line: usize, column_begin: usize, column_end: usize, spaced: bool)

enum Token:
    Name(TokenState, str)
    String(TokenState, str)
    Int(TokenState, str)
    Symbol(TokenState, str)


type Line: (line: usize, indent: usize, comment: str, tokens: [Token])


func main() -> ():
    match char "5":
        case "0": bytes.print("zero\n")
        case "1": bytes.print("one\n")
        case "2": bytes.print("two\n")
        case "3": bytes.print("three\n")
        case "4": bytes.print("four\n")
        case "5": bytes.print("five\n")

    bytes.print("👨‍👩‍👦‍👦\n")
    bytes.print("🔤\n")
