import os
import pytest
import sys
import sys
import textwrap


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from common import compile_full, run


def test_assert():
    assert run(f"func main() -> ():\n assert(True)", exit_ok=True)
    assert run(f"func main() -> ():\n assert(False)", exit_err=True)


@pytest.mark.parametrize(
    "code",
    [
        "i32 0 != 1",
        "i32 1 != -1",
        "i32 0 == 0",
        "i32 1 == 1",
        "i32 1 > 0",
        "i32 1 > -1",
        "i32 (-1) > -2",
        "i32 0 < 1",
        "i32 (-2) < -1",
        "i32 1 | 0 == 1",
        "i32 0 | 1 == 1",
        "i32 2 | 0 == 2",
        "i32 0 | 2 == 2",
        "i32 1 | 2 == 3",
        "i32 2 | 1 == 3",
        "i32 2 + 1 == 3",
        "i32 1 + 2 == 3",
        "i32 2 * 3 == 6",
        "i32 3 * 2 == 6",
        "i32 100 * 0 == 0",
        "i32 1 - 2 == -1",
    ],
)
def test_i32(code):
    assert run(f"func main() -> ():\n assert({code})", exit_ok=True)


@pytest.mark.parametrize(
    "code",
    [
        "i32 0 == 1",
        "i32 1 != 1",
        "i32 0 > 1",
        "i32 (-1) < -2",
        "i32 1 > 2",
        "i32 (-1) > 0",
        "i32 2 + 2 == 5",
        "i32 3 * 3 == 8",
        "i32 4 - 4 == 1",
        "i32 5 | 2 == 6",
        "i32 2 | 2 == 3",
        "i32 10 * 10 == 99",
        "i32 7 > 8",
        "i32 (-3) > 0",
        "i32 0 < -1",
        "i32 1 == -1",
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
        'assert(bytes "abc" == "abc")',
        'assert(not (bytes"abc" == "def"))',
        'assert(bytes.repeat(4, "0")[0] == byte "0")',
        'assert(bytes.len("abcd") == 4)',
        'assert(bytes.slice("abcdef", 1, 5) == "bcde")',
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


@pytest.mark.parametrize(
    "code",
    [
        "assert(not (bool (i32 0)))",
        "assert(bool(i32 1))",
        "assert(bool(i32 10))",
        "assert(bool(i32 10) == bool(i32 1))",
        "let a: bool = bool (i32 1)\nassert(a)",
        "let a: bool = __reinterpret_cast (i32 1)\nassert(a)",
        "let a: bool = bool (i32 1)\nassert(a)",
    ],
)
def test_bool_cast(code):
    assert run(f"func main() -> ():\n" + textwrap.indent(code, "    "), exit_ok=True)


@pytest.mark.parametrize(
    "code",
    [
        "let a: bool = 1",
        "let a: bool = i32 1",
        "let a: i32 = 1\nlet b: bool = a",
        "let i: i32 = True",
    ],
)
def test_bool_cast_fail(code):
    with pytest.raises(Exception):
        assert compile_full(f"func main() -> ():\n" + textwrap.indent(code, "    "))
