# TODO:
# - canonical names
# - argument/variable indexing
# - automatic __default method for tuples
# - disallow implicit conversion from tuple to named tuple
# - allow template instances as template arguments


impl[T] __native_array[T]:
    func __new_uninitialized(capacity: i32) -> Self:
        asm:
            (array.new {Self.__asm_type} {T.__default()} {capacity})


type __array[T]: (__data: __native_array[T], __len: i32)

impl[T] __array[T]:
    func new() -> Self:
        (__native_array[T].__new_uninitialized(0), 0)

    func len(self: Self) -> i32:
        self.__len

    func capacity(self: Self) -> i32:
        asm: (array.len {self.__data})

    func reserve(self: Self, additional: i32) -> ():
        let current_capacity: i32 = self.capacity()
        let required_capacity: i32 = self.__len + additional
        if required_capacity <= current_capacity:
            return

        let new_capacity: i32 = current_capacity + current_capacity // 2 + 1
        if new_capacity < required_capacity:
            new_capacity = required_capacity

        let new_data: __native_array[T] = __native_array[T].__new_uninitialized(new_capacity)
        let i: i32 = 0
        while i < self.__len:
            new_data[i] = self.__data[i]
            i = i + 1

        self.__data = new_data

    func at(self: Self, i: i32) -> T:
        assert(i < self.__len)
        self.__data[i]

    func set(self: Self, i: i32, value: T) -> ():
        assert(i < self.__len)
        self.__data[i] = value

    func append(self: Self, value: T) -> ():
        self.reserve(1)
        self.__data[self.__len] = value
        self.__len = self.__len + 1


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

    i32.print(47)
    bytes.print("\n")

    let arr: __array[i32] = __array[i32].new()
    assert(arr.len() == 0)

    arr.append(123)
    assert(arr.len() == 1)
    assert(arr.at(0) == 123)
