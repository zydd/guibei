# TODO:
# - canonical names
# - argument/variable indexing
# - automatic __default method for tuples
# - disallow implicit conversion from tuple to named tuple
# - allow template instances as template arguments


func main() -> ():
    i32(0) + 123456
    usize 1 + 0xfffffffffffffffe
    usize 0xffffffff * 0x100000000
    usize 0x100000000 * 0xffffffff
    (usize (-1)).print()
    bytes.print("\n")

    let a: i32 = 777
    bool.True
    False
