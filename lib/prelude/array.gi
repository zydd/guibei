type __array[T]: (__data: __native_array[T], __len: i32)


impl[T] __native_array[T]:
    func __new_uninitialized(capacity: i32) -> Self:
        asm:
            (array.new {Self.__asm_type} {T.__default} {capacity})


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
