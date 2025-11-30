
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


macro a() -> i32:
    let macro_local: i32 = 3
    macro_local * 2


macro b(macro_arg: i32) -> i32:
    if macro_arg >= 3:
        let mult: i32 = 2
        return macro_arg * mult
    macro_arg


func main() -> ():
    let arr: mat_arr = mat_arr.repeat(10)

    let i: i32 = 0
    while i < arr.len():
        arr[i] = mat(pair(i, b(i)), pair(a(), a()))
        i = i + 1

    i = 0
    while i < arr.len():
        arr[i].print()
        bytes.print("\n")
        i = i + 1
