
type pair: (fst: i32, snd: i32)

impl pair:
    func print(self: Self):
        bytes.print("(")
        self.0.print()
        bytes.print(", ")
        self.1.print()
        bytes.print(")")

type mat: (pair, pair)

impl mat:
    func print(self: Self):
        bytes.print("[")
        self.0.print()
        bytes.print(", ")
        self.1.print()
        bytes.print("]")

func main():
    i32(0).print()
    bytes.print(bytes.repeat(1, 10))
    i32(10).print()
    bytes.print(bytes.repeat(1, 10))
    i32.print(1234567890)
    bytes.print(bytes.repeat(1, 10))
    i32(-1234567890).print()
    bytes.print("\nHello world!\n")
    i32.print(bytes.eq("abc", "abc"))
    bytes.print("\n")
    bytes.print(bytes.read(100))
    bytes.print(bytes.repeat(1, 10))

    bytes.print("None.is_some: ")
    Option.None.is_some().print()
    bytes.print("\n")
    bytes.print("Some(3).is_some: ")
    Option.Some(3).is_some().print()
    bytes.print(" val: ")
    Option.Some(3).0.print()
    bytes.print("\n")
    bytes.print("val unwrap: ")
    let val: Option = Option.Some(123)
    val.unwrap().print()
    bytes.print("\n")
    pair(123, 456).print()
    bytes.print("\n")
    mat(pair(1, 2), pair(3, 4)).print()
    bytes.print("\n")
    pair(123, 456).0.print()
    bytes.print("\n")
    pair(123, 456).snd.print()
    bytes.print("\n")
    bytes.slice("abcdefghi", 3, 6).print()
    bytes.print("\n")
