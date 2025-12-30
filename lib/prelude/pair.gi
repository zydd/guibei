type pair: (first: u32, second: u32)


impl pair:
    # macro __default() -> Self:
    #     asm: (ref.null {Self.__asm_type})

    func eq(self, other: Self) -> bool:
        return (self.0 == other.0) && (self.1 == other.1)


    func repr(self) -> bytes:
        let res: bytes = "("
        res.append(self.first.repr())
        res.append(", ")
        res.append(self.second.repr())
        res.append(")")
        res
