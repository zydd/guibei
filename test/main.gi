type pair2[T, U]: (T, U)

func main() -> ():
    # let val: var[i32] = 10
    let val: pair2[i32, bytes] = (1, "two")
    val.0.print()
    bytes.print("\n")
    val.1.print()
    bytes.print("\n")
