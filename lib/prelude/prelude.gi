# bytes


type bytes: __native_array[byte]
type bytes2: [byte]
type str: [char]


impl bytes2:
    func new() -> Self:
        bytes2 __array[byte].new()

    func repeat(count: usize, chr: byte) -> Self:
        # FIXME: do not use __array internals
        Self (asm: (array.new {bytes.__asm_type} {chr} {count}), count)


impl bytes:
    macro __from_literal(lit: __str) -> Self:
        let arr: __native_array[u8] = __native_array[u8].__new_uninitialized(lit.__len)
        :for i, c in __enumerate(lit):
            arr[i] = c
        # bytes(arr, lit.__len)
        __reinterpret_cast arr

    func repeat(count: usize, chr: byte) -> bytes:
        asm:
            (array.new {bytes.__asm_type} {chr} {count})

    func print(self) -> ():
        let i: usize = 0
        let len: usize = asm: (array.len (local.get $self))

        while i < len:
            asm: (i32.store8 {i} {self[i]})
            i = i + 1

        # FIXME: use __stackp
        # FIXME: integral type casting
        __print_n(i32 0, __reinterpret_cast len)

    func read(count: usize) -> bytes:
        let buffer: usize = usize asm: (global.get $__stackp) + 16
        # FIXME: integral type casting
        let read_count: usize = __reinterpret_cast __read_n(__reinterpret_cast buffer, __reinterpret_cast count)
        let result: bytes = bytes.repeat(read_count, "\0")
        let i: usize = 0

        while i < read_count:
            result[i] = asm: (i32.load {buffer + i})
            i = i + 1
        return result

    func len(self) -> usize:
        asm: (array.len (local.get $self))

    func eq(self, other: Self) -> bool:
        if self.len() != other.len():
            return False

        let i: usize = 0
        while i < self.len():
            if self[i] != other[i]:
                return False
            i = i + 1

        return True

    func slice(self, start: usize, end: usize) -> bytes:
        let len: usize = self.len()
        if (start < 0) || (end < 0) || (start > len) || (end > len) || (start > end):
            asm: unreachable

        let result: bytes = bytes.repeat(end - start, "\0")
        let i: usize = start
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


# builtin


func not(a: bool) -> bool:
    asm: (i32.eqz {a})


func assert(cond: bool) -> ():
    if not cond:
        asm:
            unreachable
