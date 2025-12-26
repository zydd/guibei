# TODO:
# - Canonical names
# - Argument/variable indexing
# - Disallow implicit conversion from tuple to named tuple
# - Allow template instances as template arguments
# - Allow explicit casting between integral types: u32(char"c")
# - Array indexing


type TokenState: (line: usize, column_begin: usize, column_end: usize, spaced: bool)

enum Token:
    Name(TokenState, bytes2)
    String(TokenState, bytes2)
    Int(TokenState, bytes2)
    Symbol(TokenState, bytes2)


type Line: (line: usize, indent: usize, comment: bytes2, tokens: [Token])
impl Line:
    func new() -> Self:
        Line(0, 0, bytes2.new(), __array[Token].new())

type Tokenizer

impl Tokenizer:
    func parse(code: bytes2) -> [Line]:
        let lines: [Line] = __array[Line].new()
        let i: usize = 0
        let line: Line = Line.new()
        while i < code.len():
            code.at(i).print()

        lines

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

    let a: pair = pair(1, 2)
    match Option Option.Some(3):
        case Option.None:
            assert(False)
        case Option.Some(value):
            assert(True)
