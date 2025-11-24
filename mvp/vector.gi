trait Copy:
    func copy(self) -> Self


trait Clone:
    func clone(self) -> Self:
        self.copy()

trait Iter:
    type Type

    func next(mut self) -> Option[Type]


macro repeat[T: Copy](n: isize, value: T) -> T[]:
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



# vector


type vec[T]: (_data: T[], _len: isize)

impl[T] vec[T]:
    func len(self) -> isize:
        self._len

    func capacity(self) -> isize:
        asm: (array.len {self._data})

    func reserve(self, additional: isize):
        let current_capacity: isize = self.capacity()
        let required_capacity: isize = self._len + additional
        if required_capacity <= current_capacity:
            return

        let new_capacity: isize = current_capacity + current_capacity // 2 + 1
        if new_capacity < required_capacity:
            new_capacity = required_capacity

        let new_data: T[] = T[].__new_uninitialized(new_capacity)
        let i: isize = 0
        while i < self._len:
            new_data[i] = self._data[i]
            i = i + 1

        self._data = new_data

    func [](self, i: isize) -> T:
        assert(i < self._len)
        self.data[i]

    func [](mut self, i: isize, value: T) -> T:
        assert(i < self._len)
        self.data[i] = value
