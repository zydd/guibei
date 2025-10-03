import functools
import linecache
import re
import sys


class IncompleteParse(Exception):
    pass


def generate(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        def parser(input):
            initial_pos = input.pos
            gen = f(*args, **kwargs)
            result = None
            try:
                while True:
                    p = gen.send(result)
                    result, input = p(input)
            except StopIteration as e:
                return e.value, input
            except ValueError as e:
                frame_lineno = gen.gi_frame.f_lineno
                filename = gen.gi_code.co_filename
                context = ""
                context += f"In parser {f.__name__}\n"
                context += f"{filename}:{frame_lineno}\n"

                for lineno in range(frame_lineno - 3, frame_lineno + 2):
                    line = linecache.getline(filename, lineno).strip("\n")
                    prefix = "->" if lineno == frame_lineno else "  "
                    context += f"{lineno:4}: {prefix} {line}\n"

                context += "\n"
                context += e.args[0]

                if input.pos != initial_pos:
                    raise IncompleteParse(context) from e
                else:
                    raise ValueError(context) from e

        return parser

    return wrapper


def string(s):
    def parser(input):
        if input.startswith(s):
            return s, input.advance(len(s))
        else:
            found = repr(input.current()[0]) if input.current() else "{eof}"
            raise ValueError(input.context() + f"\nExpected {repr(s)}, found {found}")

    return parser


def regex(pattern, group=0):
    compiled = re.compile(pattern)

    def parser(input):
        match = compiled.match(input.current())
        if match:
            return match.group(group), input.advance(len(match.group(0)))
        else:
            found = repr(input.current()[0]) if input.current() else "{eof}"
            raise ValueError(input.context() + f"\nExpected pattern /{pattern}/, found {found}")

    return parser


def choice(*parsers):
    def parser(input):
        last_error = None
        for p in parsers:
            try:
                return p(input)
            except ValueError as e:
                last_error = e
        raise last_error

    return parser


def many(p):
    def parser(input):
        results = []
        while True:
            try:
                result, input = p(input)
                results.append(result)
            except (ValueError, IncompleteParse):
                break
        return results, input

    return parser


def optional(p):
    def parser(input):
        try:
            return p(input)
        except (ValueError, IncompleteParse):
            return None, input

    return parser


def sequence(*parsers):
    def parser(input):
        results = []
        for p in parsers:
            result, input = p(input)
            results.append(result)
        return results, input

    return parser


def sep_by(sep, p):
    def parser(input):
        results = []
        try:
            result, input = p(input)
            results.append(result)
        except ValueError:
            return results, input

        while True:
            try:
                _, input = sep(input)
            except (ValueError, IncompleteParse):
                break
            try:
                result, input = p(input)
            except ValueError:
                break
            results.append(result)
        return results, input

    return parser


def backtrack(p):
    def parser(input):
        try:
            return p(input)
        except IncompleteParse as e:
            raise ValueError("backtrack") from e

    return parser

def debug_context():
    def parser(input):
        print(input.context(), file=sys.stderr)
        return None, input

    return parser


def debug_current(n):
    def parser(input):
        return input.current()[:n], input

    return parser


@generate
def between(open, close, content):
    yield open
    result = yield content
    yield close
    return result


newline = string("\n")
brackets = lambda p: between(string("["), string("]"), p)
bracers = lambda p: between(string("{"), string("}"), p)
