
type mat: (pair, pair)

impl mat:
    func print(self: Self) -> ():
        bytes.print("[")
        self.0.print()
        bytes.print(", ")
        self.1.print()
        bytes.print("]")

type mat_arr: mat[]

impl mat_arr:
    func len(self: Self) -> i32:
        asm: (array.len (local.get $self))

    func repeat(count: i32) -> Self:
        let default: mat = mat(pair(0, 0), pair(0, 0))
        asm: (array.new {Self.__asm_type} {default} {count})


macro a -> i32:
    let val: i32 = 3
    if val > 0:
        let mult: i32 = 2
        val = val * mult
    val


# Macro return -> block result
macro b(val: i32) -> i32:
    if val > 0:
        let mult: i32 = 2
        val = val * mult
    val


func main() -> ():
    let arr: mat_arr = mat_arr.repeat(10)
    let i: i32 = 0
    arr[3] = mat(pair(3, 3), pair(3, 3))
    while i < arr.len():
        arr[i].print()
        bytes.print("\n")
        i = i + 1
