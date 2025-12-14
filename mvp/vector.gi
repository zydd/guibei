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
