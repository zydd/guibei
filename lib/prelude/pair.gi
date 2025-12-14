type pair: (first: i32, second: i32)


impl pair:
    # macro __default() -> Self:
    #     asm: (ref.null {Self.__asm_type})

    func eq(self, other: Self) -> bool:
        return (self.0 == other.0) && (self.1 == other.1)

    func print(self) -> ():
        bytes.print("(")
        self.0.print()
        bytes.print(", ")
        self.1.print()
        bytes.print(")")

