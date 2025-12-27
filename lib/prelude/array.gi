type __array[T]: (__data: __native_array[T], __len: usize)


impl[T] __native_array[T]:
    func __new_uninitialized(capacity: usize) -> Self:
        asm:
            (array.new {Self.__asm_type} {T.__default} {capacity})

    :[builtin]
    func [](self, i: usize) -> T

    :[builtin]
    func []=(self: Self, i: usize, value: T) -> ()


impl[T] __array[T]:
    func new() -> Self:
        Self(__native_array[T].__new_uninitialized(0), 0)

    func len(self: Self) -> usize:
        self.__len

    func capacity(self: Self) -> usize:
        asm: (array.len {self.__data})

    func reserve(self: Self, additional: usize) -> ():
        let current_capacity: usize = self.capacity()
        let required_capacity: usize = self.__len + additional
        if required_capacity <= current_capacity:
            return

        let new_capacity: usize = current_capacity + current_capacity // 2 + 1
        if new_capacity < required_capacity:
            new_capacity = required_capacity

        let new_data: __native_array[T] = __native_array[T].__new_uninitialized(new_capacity)
        let i: usize = 0
        while i < self.__len:
            new_data[i] = self.__data[i]
            i = i + 1

        self.__data = new_data

    func at(self: Self, i: usize) -> T:
        assert(i < self.__len)
        self.__data[i]

    func set(self: Self, i: usize, value: T) -> ():
        assert(i < self.__len)
        self.__data[i] = value

    func append(self: Self, value: T) -> ():
        self.reserve(1)
        self.__data[self.__len] = value
        self.__len = self.__len + 1

    func [](self, i: usize) -> T:
        assert(i < self.__len)
        self.__data[i]

    func []=(self: Self, i: usize, value: T) -> ():
        assert(i < self.__len)
        self.__data[i] = value
