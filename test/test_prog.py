import os
import pprint
import pytest
import sys
import sys
import textwrap


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

import parser
import compiler
from compiler import ir, codegen
import tempfile
import subprocess


prelude = open(os.path.join(base_dir, "lib/prelude.gi"), "r", encoding="utf8").read()


def run(code, exit_ok=None, exit_err=None, stdout=None):
    prog = parser.parse_str(prelude + code)
    if not prog:
        return 1

    module = compiler.semantic_pass(prog)
    # pprint.pp(module)
    module = codegen.translate_wasm(module)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".wast", delete=False) as out:
        out.write(codegen.wasm_repr_indented(module))
        out.flush()

        result = subprocess.run(
            ["wasmtime", "-Wgc", out.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if exit_ok is True:
            assert result.returncode == 0, "Execution failed"

        if exit_err is True:
            assert result.returncode != 0, "Execution succeeded while expecting failure"

        if stdout is not None:
            assert result.stdout == stdout

        print(out.name)
        print(result.stdout)
        out.close()
        os.remove(out.name)
        return result


def test_assert():
    assert run(f"func main() -> ():\n assert(10)", exit_ok=True)
    assert run(f"func main() -> ():\n assert(1)", exit_ok=True)
    assert run(f"func main() -> ():\n assert(0)", exit_err=True)


@pytest.mark.parametrize(
    "code",
    [
        "0 != 1",
        "1 != -1",
        "0 == 0",
        "1 == 1",
        "1 > 0",
        "1 > -1",
        "-1 > -2",
        "0 < 1",
        "-2 < -1",
        "1 | 0 == 1",
        "0 | 1 == 1",
        "2 | 0 == 2",
        "0 | 2 == 2",
        "1 | 2 == 3",
        "2 | 1 == 3",
        "2 + 1 == 3",
        "1 + 2 == 3",
        "2 * 3 == 6",
        "3 * 2 == 6",
        "100 * 0 == 0",
        "1 - 2 == -1",
    ],
)
def test_i32(code):
    assert run(f"func main() -> ():\n assert({code})", exit_ok=True)


@pytest.mark.parametrize(
    "code",
    [
        "0 == 1",
        "1 != 1",
        "0 > 1",
        "-1 < -2",
        "1 > 2",
        "-1 > 0",
        "2 + 2 == 5",
        "3 * 3 == 8",
        "4 - 4 == 1",
        "5 | 2 == 6",
        "2 | 2 == 3",
        "10 * 10 == 99",
        "7 > 8",
        "-3 > 0",
        "0 < -1",
        "1 == -1",
    ],
)
def test_i32_fail(code):
    assert run(f"func main() -> ():\n assert({code})", exit_err=True)


@pytest.mark.parametrize(
    "code",
    [
        "assert(Option.Some(3).0 == 3)",
        "assert(Option.Some(3).is_some())",
        "assert(not (Option.None.is_some()))",
        "let opt: Option = Option.None\nassert(not (opt.is_some()))",
        "let opt: Option = Option.Some(3)\nassert(opt.is_some())",
    ],
)
def test_option(code):
    assert run(f"func main() -> ():\n" + textwrap.indent(code, "    "), exit_ok=True)


@pytest.mark.parametrize(
    "code",
    [
        'assert(bytes.eq("abc", "abc"))',
        'assert(not (bytes.eq("abc", "def")))',
        "assert(i32 bytes.repeat(4, 13)[0] == 13)",
        "assert(i32(bytes.repeat(4, 13)[0]) != 4)",
        'assert(bytes.len("abcd") == 4)',
        'assert(bytes.eq(bytes.slice("abcdef", 1, 5), "bcde"))',
    ],
)
def test_bytes(code):
    res = run(f"func main() -> ():\n" + textwrap.indent(code, "    "), exit_ok=True)
    assert res


@pytest.mark.parametrize(
    "code, stdout",
    [
        ('bytes.print("abcd")', "abcd"),
        ('bytes.print("")', ""),
        ('bytes.print("Hello World!\\n")', "Hello World!\n"),
        ("i32.print(0)", "0"),
        ("i32.print(-1)", "-1"),
        ("i32.print(123456789)", "123456789"),
        ("i32.print(-123456789)", "-123456789"),
        ("pair(123, 456).print()", "(123, 456)"),
    ],
)
def test_print(code, stdout):
    res = run(f"func main() -> ():\n" + textwrap.indent(code, "    "), exit_ok=True, stdout=stdout)


@pytest.mark.parametrize(
    "code",
    [
        "assert(pair(123, 456).eq(pair(123, 456)))",
        "assert(pair(123, 456).0 == 123)",
        "assert(pair(123, 456).1 == 456)",
        "assert(pair(123, 456).first == 123)",
        "assert(pair(123, 456).second == 456)",
    ],
)
def test_pair(code):
    assert run(f"func main() -> ():\n" + textwrap.indent(code, "    "), exit_ok=True)


@pytest.mark.parametrize(
    "file",
    [
        os.path.join(base_dir, "test/programs", fname)
        for fname in os.listdir(os.path.join(base_dir, "test/programs"))
        if fname.endswith(".gi")
    ],
)
def test_programs(file):
    assert run(open(file, "r", encoding="utf8").read(), exit_ok=True)


@pytest.mark.skip
@pytest.mark.parametrize(
    "code",
    [
        "let a: i32 = 256\nassert(i32(i8(a)) == 0)",
    ],
)
def test_integer_narrowing(code):
    assert run(f"func main() -> ():\n" + textwrap.indent(code, "    "), exit_ok=True)


@pytest.mark.skip
@pytest.mark.parametrize(
    "code",
    [
        "i8(256)",
    ],
)
def test_integer_narrowing_fail(code):
    assert run(f"func main() -> ():\n" + textwrap.indent(code, "    "), exit_err=True)
