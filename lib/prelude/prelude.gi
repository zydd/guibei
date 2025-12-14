# bytes


type bytes: __native_array[i8]
type str: [u8]


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


# builtin


func not(a: bool) -> bool:
    asm: (i32.eqz {a})


func assert(cond: bool) -> ():
    if not cond:
        asm:
            unreachable
