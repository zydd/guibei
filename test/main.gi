# main.gi

# TODO:
# - Canonical names
# - Argument/variable indexing
# - Disallow implicit conversion from tuple to named tuple
# - Allow template instances as template arguments
# - Allow explicit casting between integral types: u32(char"c")
# - Array indexing


type TokenState: (line: usize, column_begin: usize, column_end: usize, spaced: bool)

enum Token:
    Name(TokenState, bytes)
    String(TokenState, bytes)
    Int(TokenState, bytes)
    Symbol(TokenState, bytes)


type Line: (line: usize, indent: usize, comment: bytes, tokens: [Token])
impl Line:
    func new() -> Self:
        Line(0, 0, bytes.new(), __array[Token].new())

type Tokenizer

impl Tokenizer:
    func parse(code: bytes) -> [Line]:
        let lines: [Line] = __array[Line].new()
        let i: usize = 0
        let line: Line = Line.new()
        while i < code.len():
            code[i].print()

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

    let fd: File = File.open_ro("main.gi")
    let read: bytes = fd.read(65536)
    fd.close()

    bytes.print("\nread: ")
    usize.print(read.len())
    bytes.print("\n")
    bytes.print(read.slice(0, 10))
    bytes.print("\n")

    let arr: [byte] = __array[byte].new()
    arr.append("z")
    arr.append(48)
    u8.print(arr[1])
    bytes.print("\n")
