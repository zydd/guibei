# TODO:
# - Canonical names
# - Argument/variable indexing
# - Disallow implicit conversion from tuple to named tuple
# - Allow template instances as template arguments
# - Allow explicit casting between integral types


type TokenState: (line: usize, column_begin: usize, column_end: usize, spaced: bool)

enum Token:
    Name(TokenState, str)
    String(TokenState, str)
    Int(TokenState, str)
    Symbol(TokenState, str)


type Line: (line: usize, indent: usize, comment: str, tokens: [Token])



func main() -> ():
    i32(0) + 123456
    usize 1 + 0xfffffffffffffffe
    usize 0xffffffff * 0x100000000
    usize 0x100000000 * 0xffffffff
    (usize (-1)).print()
    bytes.print("\n")

    let a: bool = bool 0

    bool.True
    False
    assert(Option.Some(3).0 == 3)
    assert(not Option.None.is_some())
    assert(pair(123, 456).first == 123)

    u32.print(u32 "1")
    bytes.print("\n")

    let arr: __array[i32] = __array[i32].new()
    assert(arr.len() == 0)

    arr.append(123)
    assert(arr.len() == 1)
    assert(arr.at(0) == 123)

    let arr: [pair] = __array[pair].new()
    assert(arr.len() == 0)

    arr.append((123, 456))
    assert(arr.len() == 1)
    assert(arr.at(0).0 == 123)
