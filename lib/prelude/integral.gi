type i8: __integral[i32, i8, array.get_s]
type u8: __integral[i32, i8, array.get_u]
type i16: __integral[i32, i16, array.get_s]
type u16: __integral[i32, i16, array.get_u]
type i32: __integral[i32, i32, array.get]
type u32: __integral[i32, i32, array.get]
type i64: __integral[i64, i64, array.get]
type u64: __integral[i64, i64, array.get]
type f32: __integral[f32, f32, array.get]
type f64: __integral[f64, f64, array.get]
type isize: __integral[i64, i64, array.get]
type usize: __integral[i64, i64, array.get]


impl i8:
    macro __from_literal(i: __int) -> i8:
        asm:
            (i32.const {i})

    func (==)(self, rhs: Self) -> bool:
        asm: (i32.eq {self} {rhs})

    func (!=)(self, rhs: Self) -> bool:
        asm: (i32.ne {self} {rhs})


impl i32:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__leq(0x7fffffff)
        asm:
            (i32.const {i})

    macro __cast_from(i: i8) -> Self:
        __reinterpret_cast i

    func (*)(self, rhs: Self) -> Self:
        asm: (i32.mul {self} {rhs})

    func (//)(self, rhs: Self) -> Self:
        asm: (i32.div_s {self} {rhs})

    func (%)(self, rhs: Self) -> Self:
        asm: (i32.rem_s {self} {rhs})

    func (+)(self, rhs: Self) -> Self:
        asm: {self} {rhs} i32.add

    func (-)(self, rhs: Self) -> Self:
        asm: (i32.sub {self} {rhs})

    func (&)(self, rhs: Self) -> Self:
        asm: (i32.and {self} {rhs})

    func (|)(self, rhs: Self) -> Self:
        asm: (i32.or {self} {rhs})

    func (<)(self, rhs: Self) -> bool:
        asm: (i32.lt_s {self} {rhs})

    func (<=)(self, rhs: Self) -> bool:
        asm: (i32.le_s {self} {rhs})

    func (>)(self, rhs: Self) -> bool:
        asm: (i32.gt_s {self} {rhs})

    func (>=)(self, rhs: Self) -> bool:
        asm: (i32.ge_s {self} {rhs})

    func (==)(self, rhs: Self) -> bool:
        asm: (i32.eq {self} {rhs})

    func (!=)(self, rhs: Self) -> bool:
        asm: (i32.ne {self} {rhs})

    func print(self) -> ():
        let n: i32 = self
        let i: i32 = 20
        let len: i32 = 0
        let buffer: i32 = i32 asm: (global.get $__stackp) + 16

        if n == 0:
            asm: (i32.store8 {buffer} (i32.const 48))
            __print_n(buffer, 1)
            return

        if self < 0:
            n = 0 - n

        while n:
            asm: (i32.store8 {buffer + i} {n % 10 + 48})
            i = i - 1
            len = len + 1
            n = n // 10

        i = 0
        if self < 0:
            asm: (i32.store8 {buffer + i} {i32 45})
            i = i + 1
            len = len + 1

        while i < len:
            asm: (i32.store8 {buffer + i} (i32.load {buffer + 21 + i - len}))
            i = i + 1

        __print_n(buffer, len)


impl u32:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__geq(0)
        # static_assert val.__leq(0xffffffff)
        asm:
            (i32.const {i})

    func (*)(self, rhs: Self) -> Self:
        asm: (i32.mul {self} {rhs})

    func (//)(self, rhs: Self) -> Self:
        asm: (i32.div_u {self} {rhs})

    func (%)(self, rhs: Self) -> Self:
        asm: (i32.rem_u {self} {rhs})

    func (+)(self, rhs: Self) -> Self:
        asm: (i32.add {self} {rhs})

    func (-)(self, rhs: Self) -> Self:
        asm: (i32.sub {self} {rhs})

    func (&)(self, rhs: Self) -> Self:
        asm: (i32.and {self} {rhs})

    func (|)(self, rhs: Self) -> Self:
        asm: (i32.or {self} {rhs})

    func (<)(self, rhs: Self) -> bool:
        asm: (i32.lt_u {self} {rhs})

    func (<=)(self, rhs: Self) -> bool:
        asm: (i32.le_u {self} {rhs})

    func (>)(self, rhs: Self) -> bool:
        asm: (i32.gt_u {self} {rhs})

    func (>=)(self, rhs: Self) -> bool:
        asm: (i32.ge_u {self} {rhs})

    func (==)(self, rhs: Self) -> bool:
        asm: (i32.eq {self} {rhs})

    func (!=)(self, rhs: Self) -> bool:
        asm: (i32.ne {self} {rhs})

    func print(self) -> ():
        let n: Self = self
        let i: Self = 20
        let len: Self = 0
        let buffer: Self = Self asm: (global.get $__stackp) + 16

        if n == 0:
            asm: (i32.store8 {buffer} (i32.const 48))
            __print_n(__reinterpret_cast buffer, 1)
            return

        while n:
            asm: (i32.store8 {buffer + i} {n % 10 + 48})
            i = i - 1
            len = len + 1
            n = n // 10

        i = 0
        while i < len:
            asm: (i32.store8 {buffer + i} (i32.load {buffer + 21 + i - len}))
            i = i + 1

        __print_n(__reinterpret_cast buffer, __reinterpret_cast len)


impl i64:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__leq(0x7fffffffffffffff)
        asm:
            (i64.const {i})


impl usize:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__geq(0)
        # static_assert val.__leq(0xffffffffffffffff)
        asm:
            (i64.const {i})

    func (*)(self, rhs: Self) -> Self:
        assert((rhs == 0) || (self <= asm: (i64.div_u {usize 0xffffffffffffffff} {rhs})))
        asm: (i64.mul {self} {rhs})

    func (+)(self, rhs: Self) -> Self:
        let res: Self = asm: (i64.add {self} {rhs})
        assert(asm: (i64.gt_u {res} {self}))
        res

    func (//)(self, rhs: Self) -> Self:
        asm: (i64.div_u {self} {rhs})

    func (%)(self, rhs: Self) -> Self:
        asm: (i64.rem_u {self} {rhs})

    func (-)(self, rhs: Self) -> Self:
        let res: Self = asm: (i64.sub {self} {rhs})
        assert(asm: (i64.lt_u {res} {self}))
        res

    func (&)(self, rhs: Self) -> Self:
        asm: (i64.and {self} {rhs})

    func (|)(self, rhs: Self) -> Self:
        asm: (i64.or {self} {rhs})

    func (<)(self, rhs: Self) -> bool:
        asm: (i64.lt_u {self} {rhs})

    func (<=)(self, rhs: Self) -> bool:
        asm: (i64.le_u {self} {rhs})

    func (>)(self, rhs: Self) -> bool:
        asm: (i64.gt_u {self} {rhs})

    func (>=)(self, rhs: Self) -> bool:
        asm: (i64.ge_u {self} {rhs})

    func (==)(self, rhs: Self) -> bool:
        asm: (i64.eq {self} {rhs})

    func (!=)(self, rhs: Self) -> bool:
        asm: (i64.ne {self} {rhs})

    func print(self) -> ():
        let n: Self = self
        let i: i32 = 20
        let len: i32 = 0
        let buffer: i32 = i32 asm: (global.get $__stackp) + 16

        if n == 0:
            asm: (i32.store8 {buffer} (i32.const 48))
            __print_n(buffer, 1)
            return

        if self < 0:
            n = 0 - n

        while n != 0:
            asm: (i32.store8 {buffer + i} (i32.wrap_i64 {n % 10 + 48}))
            i = i - 1
            len = len + 1
            n = n // 10

        i = 0
        if self < 0:
            asm: (i32.store8 {buffer + i} {i32 45})
            i = i + 1
            len = len + 1

        while i < len:
            asm: (i32.store8 {buffer + i} (i32.load {buffer + 21 + i - len}))
            i = i + 1

        __print_n(buffer, len)
