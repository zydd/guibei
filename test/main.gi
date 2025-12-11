# TODO:
# - canonical names
# - argument/variable indexing
# - operator overloading
# - automatic __default method for tuples
# - disallow implicit conversion from tuple to named tuple
# - allow template instances as template arguments

type usize

impl usize:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__geq(0)
        # static_assert val.__leq(0xffffffffffffffff)
        asm:
            (i64.const {i})

    macro __type_reference() -> ():
        asm:
            i64

    func __default() -> Self:
        0

    func (+)(self: Self, rhs: Self) -> Self:
        asm: (i64.add {self} {rhs})


func main() -> ():
    i32(0) + 1
    usize(0) + 1
