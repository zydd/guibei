type pair2[T, U]: (T, U)

# type pair3: pair2[i32, i32]

type array[T]

impl[T] array[T]:
    macro __type_declaration() -> ():
        asm:
            (array (mut {T.__type_reference}))

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


type vec[T]: (__data: array[T], __len: i32)

impl[T] vec[T]:
    func new() -> Self:
        (asm: (array.new_default {array[T].__asm_type} (i32.const 0)), 0)


    func len(self: Self) -> i32:
        self.__len

# TODO: canonical names


func main() -> ():
    let val: array[i32] = asm: (array.new_default $root.module.array.$root.module.i32 {i32 10})
    assert(val.len() == 10)

    let val2: array[pair] = asm: (array.new $root.module.array.$root.module.pair {pair(1, 2)} {i32 12})
    assert(val2.len() == 12)

    let val3: vec[i32] = vec[i32].new()
    assert(val3.len() == 0)
