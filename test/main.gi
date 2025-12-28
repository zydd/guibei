# main.gi

# TODO:
# - Canonical names
# - Argument/variable indexing
# - Disallow implicit conversion from tuple to named tuple
# - Allow template instances as template arguments
# - Allow explicit casting between integral types: u32(char"c")


type TokenState: (line: usize, column_begin: usize, column_end: usize, spaced: bool)


enum Token:
    Name(TokenState, bytes)
    String(TokenState, bytes)
    Int(TokenState, bytes)
    Symbol(TokenState, bytes)
    None

impl Token:
    func repr(self) -> bytes:
        "Token"


type Line: (line: usize, indent: usize, comment: bytes, tokens: [Token])
impl Line:
    func new(nr: usize) -> Self:
        Line(nr, 0, "", __array[Token].new())

    func repr(self) -> bytes:
        let res: bytes = "Line(line: "
        res.append(self.line.repr())
        res.append(", indent: ")
        res.append(self.indent.repr())
        res.append(", comment: ")
        res.append(self.comment.repr())
        res.append(", ")
        res.append(self.tokens.repr())
        res.append(")")
        res


type Tokenizer: (i: usize, lines: [Line], current: Line)

impl Tokenizer:
    func new() -> Self:
        Self(0, __array[Line].new(), Line.new(0))

    func new_line(self) -> ():
        self.lines.append(self.current)

        # Line number starts from 1
        self.current = Line.new(self.lines.len() + 1)

    func parse(self, code: bytes) -> ():
        while self.i < code.len():
            if code[self.i] == "#":
                self.current.comment = self.parse_comment(code)
                self.new_line()
            else:
                if code[self.i] == "\n":
                    self.new_line()

            self.i = self.i + 1

    func parse_comment(self, code: bytes) -> bytes:
        let start: usize = self.i
        while self.i < code.len() && code[self.i] != "\n":
            self.i = self.i + 1
        code.slice(start, self.i)


func main() -> ():
    let fd: File = File.open_ro("main.gi")
    let code: bytes = fd.read(65536)

    bytes.print("\nread: ")
    usize.print(code.len())
    bytes.print("\n")

    let tk: Tokenizer = Tokenizer.new()
    tk.parse(code.slice(0, 245))

    bytes.print("\n")

    let i: usize = 0
    while i < tk.lines.len():
        tk.lines[i].repr().print()
        bytes.print("\n")
        i = i + 1

    bytes.print("\n")
