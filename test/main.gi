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
    code.len().repr().print()
    bytes.print("\n")

    bytes.print("\n")
    let tokens: [Token] = Tokenizer.parse(code)

    tokens.repr().print()

    bytes.print("\n")
