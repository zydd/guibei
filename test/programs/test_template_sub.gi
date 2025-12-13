type array[T]: __native_array[T]

impl[T] array[T]:
    func __new_uninitialized(capacity: i32) -> Self:
        asm:
            (array.new {Self.__asm_type} {T.__default()} {capacity})

    func len(self: Self) -> i32:
        asm:
            (array.len {self})

    func is_empty(self: Self) -> bool:
        self.len() == 0

    func at(self: Self, i: i32) -> T:
        asm:
            (array.get {Self.__asm_type} {self} {i})
    
    func set(self: Self, i: i32, value: T) -> ():
        asm:
            (array.set {Self.__asm_type} {self} {i} {value})


type vec[T]: (__data: array[T], __len: i32)

impl[T] vec[T]:
    func new() -> Self:
        (array[T].__new_uninitialized(0), 0)

    func len(self: Self) -> i32:
        self.__len

    func capacity(self: Self) -> i32:
        asm: (array.len {self.__data})

    func reserve(self: Self, additional: i32) -> ():
        let current_capacity: i32 = self.capacity()
        let required_capacity: i32 = self.__len + additional
        if required_capacity <= current_capacity:
            return

        let new_capacity: i32 = current_capacity + current_capacity // 2 + 1
        if new_capacity < required_capacity:
            new_capacity = required_capacity

        let new_data: array[T] = array[T].__new_uninitialized(new_capacity)
        let i: i32 = 0
        while i < self.__len:
            new_data.set(i, self.__data.at(i))
            i = i + 1

        self.__data = new_data

    func at(self: Self, i: i32) -> T:
        assert(i < self.__len)
        self.__data.at(i)

    func set(self: Self, i: i32, value: T) -> ():
        assert(i < self.__len)
        self.__data.set(i, value)

    func append(self: Self, value: T) -> ():
        self.reserve(1)
        self.__data.set(self.__len, value)
        self.__len = self.__len + 1


func main() -> ():
    let arr: vec[i32] = vec[i32].new()
    assert(arr.len() == 0)

    arr.append(123)
    assert(arr.len() == 1)
    assert(arr.at(0) == 123)

    let arr2: vec[pair] = vec[pair].new()
    assert(arr2.len() == 0)

    arr2.append((123, 456))
    assert(arr2.len() == 1)
    assert(arr2.at(0).eq((123, 456)))

    arr2.append((789, 100))
    assert(arr2.len() == 2)
    assert(arr2.at(1).eq((789, 100)))
