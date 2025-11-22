
asm:
    (export "memory" (memory $memory))
    (export "_start" (func $module.main))
    (memory $memory 1)
    (global $__stackp (mut i32) (i32.const 1024))
    (type $vtd (array (mut funcref)))
    (global (ref $vtd) (array.new_default $vtd (i32.const 13)))
    (type $__enum (sub (struct (field i32))))
    (type $__string_literal (array (mut i8)))

# i32


type i32: __native_type<i32>


func (+)(a: i32, b: i32) -> i32:
    asm: {a} {b} i32.add


func (-)(a: i32, b: i32) -> i32:
    asm: (i32.sub {a} {b})


func (<)(a: i32, b: i32) -> i32:
    asm: (i32.lt_s {a} {b})


func (>)(a: i32, b: i32) -> i32:
    asm: (i32.gt_s {a} {b})


func (/)(a: i32, b: i32) -> i32:
    asm: (i32.div_s {a} {b})


func (%)(a: i32, b: i32) -> i32:
    asm: (i32.rem_s {a} {b})


func (==)(a: i32, b: i32) -> i32:
    asm: (i32.eq {a} {b})


func (!=)(a: i32, b: i32) -> i32:
    asm: (i32.ne {a} {b})


func (|)(a: i32, b: i32) -> i32:
    asm: (i32.or {a} {b})


impl i32:
    # func __from_literal(i: __int_literal):
    #     asm:
    #         (i32.const {i})

    func print(self: Self):
        let n: i32 = self
        let i: i32 = 20
        let len: i32 = 0
        let buffer: i32 = asm: (global.get $__stackp) + 16

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
            n = n / 10

        i = 0
        if self < 0:
            asm: (i32.store8 {buffer + i} {i32 45})
            i = i + 1

        while i < len:
            asm: (i32.store8 {buffer + i} (i32.load {buffer + 21 + i - len}))
            i = i + 1

        __print_n(buffer, len)


# bytes


type i8: __native_type<i8>
type bytes: i8[]
type str: bytes

impl bytes:
    # func __from_literal(i: __int_literal):
    #     asm:
    #         (i32.const {i})

    func repeat(count: i32, chr: i32) -> bytes:
        asm:
            (array.new {bytes.__asm_type} {chr} {count})

    func print(self: Self):
        let i: i32 = 0
        let len: i32 = asm: (array.len (local.get $self))

        while i < len:
            asm: (i32.store8 {i} {self[i]})
            i = i + 1

        __print_n(0, len)

    func read(count: i32) -> bytes:
        let buffer: i32 = asm: (global.get $__stackp) + 16
        let read_count: i32 = __read_n(buffer, count)
        let result: bytes = bytes.repeat(read_count, 0)
        let i: i32 = 0

        while i < read_count:
            result[i] = asm: (i32.load {buffer + i})
            i = i + 1
        return result

    func len(self: Self) -> i32:
        asm: (array.len (local.get $self))

    func eq(self: Self, other: Self) -> i32:
        if self.len() != other.len():
            return 0

        let i: i32 = 0
        while i < self.len():
            if self[i] != other[i]:
                return 0
            i = i + 1

        return 1

    func slice(self: Self, start: i32, end: i32) -> bytes:
        let len: i32 = self.len()
        if start < 0 | end < 0 | start > len | end > len | start > end:
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
    func is_some(self: Self) -> i32:
        match self:
            case Option.None:
                return 0
            case Option.Some(_):
                return 1
        asm: unreachable

    func unwrap(self: Self) -> i32:
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


func __print_n(addr: i32, count: i32):
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count})

    __wasi_fd_write(1, asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))


func __read_n(addr: i32, count: i32) -> i32:
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count - 1})

    __wasi_fd_read(0, asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))

    asm:
        (i32.load (global.get $__stackp))
