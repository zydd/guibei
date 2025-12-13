
asm:
    (export "memory" (memory $memory))
    (export "_start" (func $root.main))
    (memory $memory 1)
    (global $__stackp (mut i32) (i32.const 1024))
    (type $vtd (array (mut funcref)))
    (global (ref $vtd) (array.new_default $vtd (i32.const 13)))
    (type $__enum (sub (struct (field i32))))
    (type $__string_literal (array (mut i8)))


type __enum_discr: i32
impl __enum_discr:
    macro __from_literal(i: __int) -> Self:
        asm: (i32.const {i})

type __array_index: i32


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


# i32

func not(a: bool) -> bool:
    asm: (i32.eqz {a})


impl i32:
    macro __from_literal(i: __int) -> i32:
        # static_assert val.__leq(0x7fffffff)
        asm:
            (i32.const {i})

    macro __cast_from(i: i8) -> Self:
        __reinterpret_cast i

    func __default() -> Self:
        0

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


impl i64:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__leq(0x7fffffffffffffff)
        asm:
            (i64.const {i})


impl u32:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__geq(0)
        # static_assert val.__leq(0xffffffff)
        asm:
            (i32.const {i})

    func __default() -> Self:
        0

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


impl usize:
    macro __from_literal(i: __int) -> Self:
        # static_assert val.__geq(0)
        # static_assert val.__leq(0xffffffffffffffff)
        asm:
            (i64.const {i})

    func __default() -> Self:
        0

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


enum bool:
    False
    True

const True = bool.True
const False = bool.False


impl bool:
    func __default() -> Self:
        False

    func (==)(self, rhs: Self) -> bool:
        asm: (i32.eq {self} {rhs})

    func (!=)(self, rhs: Self) -> bool:
        asm: (i32.ne {self} {rhs})

    func (&&)(self, rhs: Self) -> Self:
        asm: (i32.and {self} {rhs})

    func (||)(self, rhs: Self) -> Self:
        asm: (i32.or {self} {rhs})

    # func print(self) -> ():
    #     match self:
    #         case bool.True:
    #             bytes.print("True")
    #         case bool.False:
    #             bytes.print("False")

# bytes


impl i8:
    macro __cast_from(i: __int) -> i8:
        asm:
            (i32.const {i})

    func (!=)(self, rhs: Self) -> bool:
        asm: (i32.ne {self} {rhs})


# impl __array[i8]:
#     macro [](self, i: usize) -> i8:
#         asm:
#             (array.get_s {Self.__asm_type} {self} {i})


type bytes: [i8]
type str: bytes

impl bytes:
    # func __implicit_cast(i: __int) -> ():
    #     asm:
    #         (i32.const {i})

    func repeat(count: i32, chr: i32) -> bytes:
        asm:
            (array.new {bytes.__asm_type} {chr} {count})

    func print(self) -> ():
        let i: i32 = 0
        let len: i32 = asm: (array.len (local.get $self))

        while i < len:
            asm: (i32.store8 {i} {self[i]})
            i = i + 1

        __print_n(0, len)

    func read(count: i32) -> bytes:
        let buffer: i32 = i32 asm: (global.get $__stackp) + 16
        let read_count: i32 = __read_n(buffer, count)
        let result: bytes = bytes.repeat(read_count, 0)
        let i: i32 = 0

        while i < read_count:
            result[i] = asm: (i32.load {buffer + i})
            i = i + 1
        return result

    func len(self) -> i32:
        asm: (array.len (local.get $self))

    func eq(self, other: Self) -> bool:
        if self.len() != other.len():
            return False

        let i: i32 = 0
        while i < self.len():
            # FIXME: remove explicit cast
            if self[i] != other[i]:
                return False
            i = i + 1

        return True

    func slice(self, start: i32, end: i32) -> bytes:
        let len: i32 = self.len()
        if (start < 0) || (end < 0) || (start > len) || (end > len) || (start > end):
            asm: unreachable

        let result: bytes = bytes.repeat(end - start, 0)
        let i: i32 = start
        while i < end:
            result[i - start] = self[i]
            i = i + 1

        return result


# Option


enum Option:
    None
    Some(i32)


impl Option:
    func is_some(self) -> bool:
        match self:
            case Option.None:
                return False
            case Option.Some(_):
                return True
        asm: unreachable

    func unwrap(self) -> i32:
        match self:
            case Option.None:
                asm: unreachable
            case Option.Some(value):
                return value
        asm: unreachable

# Result


enum Result:
    Ok(i32)
    Error(bytes)


# WASI


:[import("wasi_snapshot_preview1", "fd_write")]
func __wasi_fd_write(fd: i32, iovs: i32, iovs_len: i32, out_nwritten: i32) -> i32

:[import("wasi_snapshot_preview1", "fd_read")]
func __wasi_fd_read(fd: i32, iovs: i32, iovs_len: i32, out_nread: i32) -> i32


func __print_n(addr: i32, count: i32) -> ():
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count})

    __wasi_fd_write(1, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))


func __read_n(addr: i32, count: i32) -> i32:
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count - 1})

    __wasi_fd_read(0, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))

    asm:
        (i32.load (global.get $__stackp))


# builtin


func assert(cond: bool) -> ():
    if not cond:
        asm:
            unreachable


type pair: (first: i32, second: i32)


impl pair:
    func __default() -> Self:
        (0, 0)

    func eq(self, other: Self) -> bool:
        return (self.0 == other.0) && (self.1 == other.1)

    func print(self) -> ():
        bytes.print("(")
        self.0.print()
        bytes.print(", ")
        self.1.print()
        bytes.print(")")
