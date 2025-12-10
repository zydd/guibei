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

    func __new_uninitialized(capacity: i32) -> Self:
        asm:
            (array.new_default {Self.__asm_type} {capacity})

    func len(self: Self) -> i32:
        asm:
            (array.len {self})

    func is_empty(self: Self) -> i32:
        self.len() == 0

    func at(self: Self, i: i32) -> T:
        asm:
            (array.get {Self.__asm_type} {self} {i})


type vec[T]: (__data: array[T], __len: i32)

impl[T] vec[T]:
    func new() -> Self:
        (asm: (array.new_default {array[T].__asm_type} (i32.const 0)), 0)

    func len(self: Self) -> i32:
        self.__len

    func capacity(self: Self) -> i32:
        asm: (array.len {self.__data})

    # func reserve(self: Self, additional: i32) -> ():
    #     let current_capacity: i32 = self.capacity()
    #     let required_capacity: i32 = self.__len + additional
    #     if required_capacity <= current_capacity:
    #         return

    #     let new_capacity: i32 = current_capacity + current_capacity // 2 + 1
    #     if new_capacity < required_capacity:
    #         new_capacity = required_capacity

    #     let new__data: array[T] = array[T].__new_uninitialized(new_capacity)
    #     let i: i32 = 0
    #     while i < self.__len:
    #         new__data[i] = self.__data[i]
    #         i = i + 1

    #     self.__data = new__data

    func at(self: Self, i: i32) -> T:
        assert(i < self.__len)
        self.__data.at(i)

    # func set(self: Self, i: i32, value: T) -> T:
    #     assert(i < self.__len)
    #     self.__data[i] = value

    # func append(self: Self, value: T) -> Self:
    #     self.reserve(1)
    #     self.__data[self.__len] = value
    #     self.__len = self.__len + 1


# TODO: canonical names


func main() -> ():
    # let val: array[i32] = asm: (array.new_default $root.module.array.$root.module.i32 {i32 10})
    # assert(val.len() == 10)

    # let val2: array[pair] = asm: (array.new $root.module.array.$root.module.pair {pair(1, 2)} {i32 12})
    # assert(val2.len() == 12)

    let val3: vec[i32] = vec[i32].new()
    assert(val3.len() == 0)
