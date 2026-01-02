type ParseInfo: (line: usize, column_begin: usize, column_end: usize, spaced: bool)
impl ParseInfo:
    func repr(self) -> bytes:
        let res: bytes = "ParseInfo(line: "
        res.append(self.line.repr())
        res.append(", column_begin: ")
        res.append(self.column_begin.repr())
        res.append(", column_end: ")
        res.append(self.column_end.repr())
        res.append(", spaced: ")
        res.append(self.spaced.repr())
        res.append(")")
        res


enum Token:
    NAME
    STR
    INT
    OP
    LPAR
    RPAR
    LBRACE
    RBRACE
    LSQB
    RSQB
    COMMA
    INDENT
    DEDENT

impl Token:
    func repr(self) -> bytes:
        match self:
            case Token.NAME:        return "NAME"
            case Token.STR:         return "STR"
            case Token.INT:         return "INT"
            case Token.OP:          return "OP"
            case Token.LPAR:        return "LPAR"
            case Token.RPAR:        return "RPAR"
            case Token.LBRACE:      return "LBRACE"
            case Token.RBRACE:      return "RBRACE"
            case Token.LSQB:        return "LSQB"
            case Token.RSQB:        return "RSQB"
            case Token.COMMA:       return "COMMA"
            case Token.INDENT:      return "INDENT"
            case Token.DEDENT:      return "DEDENT"
        assert False
        ""


type Line: (line: usize, indent: usize, parse_info: [ParseInfo], tokens: [Token], comment: bytes)
impl Line:
    func new(nr: usize) -> Self:
        Line(nr, 0, __array[ParseInfo].new(), __array[Token].new(), "")

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


type Tokenizer: (_line: usize, _i: usize, _indent: [usize], _spaced: bool, _parse_info: [ParseInfo], _tokens: [Token])

impl Tokenizer:
    func new() -> Self:
        let indent: [usize] = __array[usize].new()
        indent.append(0)
        Self(1, 0, indent, False, __array[ParseInfo].new(), __array[Token].new())

    func parse(code: bytes) -> [Token]:
        let tk: Tokenizer = Tokenizer.new()
        tk._parse(code)
        while tk._indent.len() != 1:
            tk._indent.pop_last()
            tk._append(tk._i, Token.DEDENT)
        tk._tokens

    func _new_line(self) -> ():
        self._line = self._line + 1

    func _append(self, start: usize, token: Token) -> ():
        self._parse_info.append(ParseInfo(self._line, start, self._i, self._spaced))
        self._tokens.append(token)

    func _is_name_start(c: byte) -> bool:
        (c >= "A" && c <= "Z") || (c >= "a" && c <= "z") || c == "_"

    func _is_name(c: byte) -> bool:
        _is_name_start(c) || _is_digit(c)

    func _is_digit(c: byte) -> bool:
        c >= "0" && c <= "9"

    func _is_symbol(c: byte) -> bool:
        # "!$%&'*+-./:;<=>?@\\^`|~" as bytes.contains(c)
        (c == "!" || c == "$" || c == "%" || c == "&" || c == "'" || c == "*" || c == "+" || c == "-"
            || c == "." || c == "/" || c == ":" || c == ";" || c == "<" || c == "=" || c == ">"
            || c == "?" || c == "@" || c == "\\" || c == "^" || c == "`" || c == "|" || c == "~")

    func _parse(self, code: bytes) -> ():
        while self._i < code.len():
            let c: byte = code[self._i]
            if c == "#":
                self._parse_comment(code)
            elif c == "\n":
                self._i = self._i + 1
                self._new_line()
                self._parse_indent(code)
            elif c == " ":
                self._i = self._i + 1
            elif c == "\"":
                self._parse_string(code)
            elif _is_name_start(c):
                self._parse_name(code)
            elif _is_digit(c):
                self._parse_int(code)
            elif c == "(":
                self._i = self._i + 1
                self._append(self._i - 1, Token.LPAR)
            elif c == ")":
                self._i = self._i + 1
                self._append(self._i - 1, Token.RPAR)
            elif c == "{":
                self._i = self._i + 1
                self._append(self._i - 1, Token.LBRACE)
            elif c == "}":
                self._i = self._i + 1
                self._append(self._i - 1, Token.RBRACE)
            elif c == "[":
                self._i = self._i + 1
                self._append(self._i - 1, Token.LSQB)
            elif c == "]":
                self._i = self._i + 1
                self._append(self._i - 1, Token.RSQB)
            elif c == ",":
                self._i = self._i + 1
                self._append(self._i - 1, Token.COMMA)
            elif _is_symbol(c):
                self._parse_op(code)
            else:
                assert2(False, "Unexpected character: " + c.repr())

            self._spaced = (c == " ")
        self

    func _parse_indent(self, code: bytes) -> ():
        let start: usize = self._i
        while self._i < code.len() && code[self._i] == " ":
            self._i = self._i + 1

        if self._i >= code.len() || code[self._i] == "\n":
            # Ignore empty lines
            return

        let indent: usize = self._i - start
        if indent > self._indent.last():
            self._append(self._i - indent, Token.INDENT)
            self._indent.append(indent)
        else:
            while indent < self._indent.last():
                self._append(self._i - indent, Token.DEDENT)
                self._indent.pop_last()
            assert2(indent == self._indent.last(), "Unexpected indentation level on line " + self._line.repr())

    func _parse_comment(self, code: bytes) -> ():
        # let start: usize = self._i
        while self._i < code.len() && code[self._i] != "\n":
            self._i = self._i + 1
        # code.slice(start, self._i)
        ()

    func _parse_name(self, code: bytes) -> ():
        let start: usize = self._i
        while self._i < code.len() && _is_name(code[self._i]):
            self._i = self._i + 1
        self._append(start, Token.NAME)

    func _parse_op(self, code: bytes) -> ():
        let start: usize = self._i
        while self._i < code.len() && _is_symbol(code[self._i]):
            self._i = self._i + 1
        self._append(start, Token.OP)

    func _parse_int(self, code: bytes) -> ():
        let start: usize = self._i
        while self._i < code.len() && _is_digit(code[self._i]):
            self._i = self._i + 1
        self._append(start, Token.INT)

    func _parse_string(self, code: bytes) -> ():
        let start: usize = self._i
        while self._i < code.len():
            self._i = self._i + 1

            let c: byte = code[self._i]
            if c == "\\":
                assert(self._i + 1 < code.len())
                self._i = self._i + 1
                # TODO:
                # assert "rnt\\\"" as bytes.contains(code[self._i])
                ()
            elif c == "\"":
                self._i = self._i + 1
                break

        self._append(start, Token.STR)
