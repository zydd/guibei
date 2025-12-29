# bytes


type bytes: [byte]
type str: [char]


impl bytes:
    macro __from_literal(lit: __str) -> Self:
        let arr: __native_array[byte] = __native_array[byte].__new_uninitialized(lit.__len)
        :for i, c in __enumerate(lit):
            arr[i] = byte c

        # FIXME: do not use __array internals
        Self (arr, lit.__len)

    func new() -> Self:
        bytes __array[byte].new()

    func len(self) -> usize:
        let super: [byte] = __reinterpret_cast self
        super.len()

    func repeat(count: usize, chr: byte) -> Self:
        # FIXME: do not use __array internals
        Self (asm: (array.new {__native_array[byte].__asm_type} {chr} {count}), count)

    func [](self, i: usize) -> byte:
        let super: [byte] = __reinterpret_cast self
        super[i]

    func []=(self, i: usize, value: byte) -> ():
        let super: [byte] = __reinterpret_cast self
        super[i] = value

    func (==)(self, other: Self) -> bool:
        if self.len() != other.len():
            return False

        let i: usize = 0
        while i < self.len():
            if self[i] != other[i]:
                return False
            i = i + 1

        return True

    func (!=)(self, other: Self) -> bool:
        not(self == other)

    func (+)(self, other: Self) -> Self:
        let combined_len: usize = self.len() + other.len()
        let res: bytes = bytes.repeat(combined_len, 0)

        let i: usize = 0
        while i < self.len():
            res[i] = self[i]
            i = i + 1

        while i < combined_len:
            res[i] = other[i - self.len()]
            i = i + 1

        res

    func slice(self, start: usize, end: usize) -> bytes:
        let len: usize = self.len()
        if (start > len) || (start > end):
            asm: unreachable

        if end > len:
            end = len

        let result: bytes = bytes.repeat(end - start, 0)
        let i: usize = start
        while i < end:
            result[i - start] = self[i]
            i = i + 1

        result

    func print(self) -> ():
        __print(self)

    func read(count: usize) -> bytes:
        let buffer: usize = usize asm: (global.get $__stackp) + 16
        # FIXME: integral type casting
        let read_count: usize = __reinterpret_cast File._read_fd(0, __reinterpret_cast buffer, __reinterpret_cast count)
        let result: bytes = bytes.repeat(read_count, 0)
        let i: usize = 0

        while i < read_count:
            result[i] = asm: (i32.load {buffer + i})
            i = i + 1

        return result

    func append(self, other: Self) -> ():
        let super: [byte] = __reinterpret_cast self
        super.reserve(other.len())

        let i: usize = 0
        while i < other.len():
            super.__data[super.__len + i] = other[i]
            i = i + 1
        super.__len = self.len() + other.len()

    func repr(self) -> bytes:
        let res: bytes = bytes.repeat(self.len() + 2, "\"")

        let i: usize = 0
        while i < self.len():
            res[i + 1] = self[i]
            i = i + 1

        res


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
