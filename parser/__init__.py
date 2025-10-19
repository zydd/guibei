from . import lang


class Input:
    def __init__(self, text, filename):
        self.text = text
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.indent = 1

    def current(self):
        return self.text[self.pos :]

    def startswith(self, s):
        return self.text.startswith(s, self.pos)

    def advance(self, n):
        new = Input(self.text, self.filename)
        new.pos = self.pos + n
        new.indent = self.indent
        segment = self.text[self.pos : self.pos + n]
        advance_lines = segment.count("\n")
        new.line = self.line + advance_lines
        if advance_lines > 0:
            last_newline = segment.rfind("\n")
            new.column = n - last_newline
        else:
            new.column = self.column + n
        return new

    def context(self):
        start = self.text.rfind("\n", 0, self.pos) + 1
        end = self.text.find("\n", self.pos)
        if end == -1:
            end = len(self.text)
        line_text = self.text[start:end]
        lineno = f"{self.line:4}"
        pointer = " " * (self.pos - start + len(lineno) + 2) + "^"
        return f"{self.filename}:{self.line}\n{lineno}: {line_text}\n{pointer}"


def run_parser(parser, text, filename="<input>"):
    result, input = parser(Input(text, filename=filename))
    if input.pos != len(input.text):
        raise ValueError("Unconsumed input:\n" + input.context())
    return result


def parse_file(filename):
    with open(filename) as f:
        text = f.read()
    return run_parser(lang.module(), text, filename=filename)


def parse_str(code):
    return run_parser(lang.module(), code)
