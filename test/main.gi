type pair2[T, U]: (T, U)


type array[T]

impl[T] array[T]:
    macro __type_declaration() -> ():
        asm:
            (array (mut i32))

    macro __type_reference() -> ():
        asm:
            (ref {Self.__asm_type})

    func len(self: Self) -> i32:
        asm:
            (array.len {self})

    func is_empty(self: Self) -> i32:
        let res: i32 = 0
        if Self.len(self) == 0:
            res = 1
        else:
            res = 0
        return res


func main() -> ():
    let val: array[i32] = asm: (array.new_default $root.module.array.$root.module.i32 {i32 10})
    val.len().print()
    bytes.print("\n")
