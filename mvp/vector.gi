trait Copy:
    func copy(self) -> Self


trait Clone:
    func clone(self) -> Self:
        self.copy()

trait Iter:
    type Type

    func next(mut self) -> Option[Type]


macro repeat[T: Copy](n: usize, value: T) -> T[]:
    [T.copy() for 0..n]


# range


type range[T]: (cur: T, max: T)

impl[T] Iter for range[T]:
    type Type: T

    func next(mut self) -> Option[T]:
        if self.cur >= self.max:
            return None

        let result: T = self.cur
        self.cur = self.cur + 1
        Some(result)


macro (..)(a: i32, b: i32):
    range(a, b)


type i32

impl i32:
    macro __type_reference:
        asm:
            i32

    macro __implicit_cast(val: __int) -> Self:
        static_assert val.__leq(0x7fffffff)
        asm:
            (i32.const {val})


# vector


type __array[T]

impl[T] __array[T]:
    macro __type_declaration:
        asm:
            (array (mut {T.__type_reference}))

    macro __type_reference:
        asm:
            (ref {Self.__asm_type})

    macro len(self) -> usize:
        asm:
            (array.len {self})


type __var_array[T]: 

impl[T] [T]:
    type __super: (__data: __array[T], __len: usize)

    func len(self) -> usize:
        self.__len

    func capacity(self) -> usize:
        asm: (array.len {self.__data})

    func reserve(mut self, additional: usize) -> &Self:
        let current_capacity: usize = self.capacity()
        let required_capacity: usize = self.__len + additional
        if required_capacity <= current_capacity:
            return

        let new_capacity: usize = current_capacity + current_capacity // 2 + 1
        if new_capacity < required_capacity:
            new_capacity = required_capacity

        mut new__data: T[] = T[].__new_uninitialized(new_capacity)
        let i: usize = 0
        while i < self.__len:
            new__data[i] = self.__data[i]
            i = i + 1

        self.__data = new__data

    func [](self, i: usize) -> T:
        assert(i < self.__len)
        self.__data[i]

    func [](mut self, i: usize, value: T) -> T:
        assert(i < self.__len)
        self.__data[i] = value

    func append(mut self, value: T) -> &Self:
        self.&reserve(1)
        self.__data[self.__len] = value
        self.__len = self.__len + 1
