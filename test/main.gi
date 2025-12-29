# main.gi

# TODO:
# - (&&) and (||) right associativity
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
    Symbol(TokenState, byte)

impl Token:
    func repr(self) -> bytes:
        match self:
            case Token.Name(st, val):
                return "Name(" + val.repr() + ", " + st.spaced.repr() + ")"

            case Token.String(st, val):
                return "String(" + val.repr() + ", " + st.spaced.repr() + ")"

            case Token.Int(st, val):
                return "Int(" + val.repr() + ", " + st.spaced.repr() + ")"

            case Token.Symbol(st, val):
                return "Symbol(" + val.repr() + ", " + st.spaced.repr() + ")"
        assert False
        ""


type Line: (line: usize, indent: usize, tokens: [Token], comment: bytes)
impl Line:
    func new(nr: usize) -> Self:
        Line(nr, 0, __array[Token].new(), "")

    func repr(self) -> bytes:
        let res: bytes = "Line(line: "
        res.append(self.line.repr())
        res.append(", indent: ")
        res.append(self.indent.repr())
        res.append(", ")
        res.append(self.tokens.repr())
        res.append(", comment: ")
        res.append(self.comment.repr())
        res.append(")")
        res


type Tokenizer: (i: usize, lines: [Line], current: Line, spaced: bool)

impl Tokenizer:
    func new() -> Self:
        Self(0, __array[Line].new(), Line.new(1), False)

    func new_line(self) -> ():
        self.lines.append(self.current)

        # Line number starts from 1
        self.current = Line.new(self.lines.len() + 1)

    func parse_indent(self, code: bytes) -> usize:
        let start: usize = self.i
        while self.i < code.len() && code[self.i] == " ":
            self.i = self.i + 1
        return self.i - start

    func state(self, start: usize) -> TokenState:
        TokenState(self.current.line, start, self.i, self.spaced)

    func _is_name_start(c: byte) -> bool:
        (c >= "A" && c <= "Z") || (c >= "a" && c <= "z") || c == "_"

    func _is_name(c: byte) -> bool:
        _is_name_start(c) || _is_digit(c)

    func _is_digit(c: byte) -> bool:
        c >= "0" && c <= "9"

    func _is_symbol(c: byte) -> bool:
        c > 32 && c < 127 && not _is_name(c)

    func parse(self, code: bytes) -> ():
        while self.i < code.len():
            let c: byte = code[self.i]
            if c == "#":
                self.current.comment = self.parse_comment(code)
            elif c == "\n":
                self.i = self.i + 1
                self.new_line()
                self.current.indent = self.parse_indent(code)
            elif c == " ":
                self.i = self.i + 1
            elif c == "\"":
                self.current.tokens.append(self.parse_string(code))
            elif _is_name_start(c):
                let name: Token.Name = self.parse_name(code)
                self.current.tokens.append(name)
            elif _is_digit(c):
                self.current.tokens.append(self.parse_int(code))
            elif _is_symbol(c):
                self.i = self.i + 1
                self.current.tokens.append(Token.Symbol(self.state(self.i - 1), c))
            else:
                c.repr().print()
                assert False

            self.spaced = (c == " ")
        self

    func parse_comment(self, code: bytes) -> bytes:
        let start: usize = self.i
        while self.i < code.len() && code[self.i] != "\n":
            self.i = self.i + 1
        code.slice(start, self.i)

    func parse_name(self, code: bytes) -> Token.Name:
        let start: usize = self.i
        while self.i < code.len() && _is_name(code[self.i]):
            self.i = self.i + 1
        Token.Name(self.state(start), code.slice(start, self.i))

    func parse_int(self, code: bytes) -> Token.Int:
        let start: usize = self.i
        while self.i < code.len() && _is_digit(code[self.i]):
            self.i = self.i + 1
        Token.Int(self.state(start), code.slice(start, self.i))

    func parse_string(self, code: bytes) -> Token.String:
        let start: usize = self.i
        while self.i < code.len():
            self.i = self.i + 1

            let c: byte = code[self.i]
            if c == "\\":
                assert(self.i + 1 < code.len())
                self.i = self.i + 1
                # TODO:
                # assert "rnt\\\"" as bytes.contains(code[self.i])
                ()
            elif c == "\"":
                self.i = self.i + 1
                break

        Token.String(self.state(start), code.slice(start + 1, self.i - 1))


func main() -> ():
    let fd: File = File.open_ro("tokens.gi")
    let code: bytes = fd.read(65536)

    bytes.print("\nread: ")
    usize.print(code.len())
    bytes.print("\n")

    let tk: Tokenizer = Tokenizer.new()
    tk.parse(code)
    tk.new_line()

    bytes.print("\n")

    let i: usize = 0
    while i < tk.lines.len():
        tk.lines[i].repr().print()
        bytes.print("\n")
        i = i + 1

    bytes.print("\n")
