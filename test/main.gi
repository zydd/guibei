# main.gi

# TODO:
# - (&&) and (||) right associativity
# - Canonical names
# - Argument/variable indexing
# - Disallow implicit conversion from tuple to named tuple
# - Allow template instances as template arguments
# - Allow explicit casting between integral types: u32(char"c")


# macro ($)[T, A](fn: func(A) -> T, arg: A) -> T:
#     fn(arg)


func main() -> ():
    let fd: File = File.open_ro("main.gi")
    let code: bytes = fd.read(65536)

    bytes.print("\nread: ")
    code.len().repr().println()
    bytes.print("\n")

    let tokens: [Token] = Tokenizer.parse(code)

    tokens.repr().println()

    bytes.print("\n")

    let res: Result[i32, bytes] = Result[i32, bytes].Ok(1337)
    assert res.is_ok()
    res.unwrap().repr().println()

    let res: Result[i32, bytes] = Result[i32, bytes].Error("no value")
    assert not(res.is_ok())
