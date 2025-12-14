type mat: (pair, pair)

impl mat:
    func print(self: Self) -> ():
        bytes.print("[")
        self.0.print()
        bytes.print(", ")
        self.1.print()
        bytes.print("]")


type mat_arr: __native_array[mat]

impl mat_arr:
    func len(self: Self) -> i32:
        asm: (array.len (local.get $self))

    func repeat(count: i32) -> Self:
        let default: mat = mat(pair(0, 0), pair(0, 0))
        asm: (array.new {Self.__asm_type} {default} {count})


func main() -> ():
    let arr: mat_arr = mat_arr.repeat(10)
    let i: i32 = 0
    arr[3] = mat(pair(3, 3), pair(3, 3))
    while i < arr.len():
        arr[i].print()
        bytes.print("\n")
        i = i + 1

    assert(arr[0].0.0 == 0)
    assert(arr[1].0.0 == 0)
    assert(arr[2].0.0 == 0)
    assert(arr[3].0.0 == 3)
    assert(arr[4].0.0 == 0)
