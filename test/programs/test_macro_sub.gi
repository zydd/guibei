macro a() -> i32:
    let macro_local: i32 = 3
    macro_local * 2


macro b(macro_arg: i32) -> i32:
    if macro_arg >= 3:
        let mult: i32 = 2
        return macro_arg * mult
    macro_arg


func main() -> ():
    assert(a() == 6)
    assert(b(2) == 2)
    assert(b(3) == 6)
    assert(a() == 6)
    assert(b(b(b(b(a())))) == 96)
