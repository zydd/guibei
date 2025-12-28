func main() -> ():
    let arr: [u32] = __array[u32].new()
    assert(arr.len() == 0)

    arr.append(123)
    assert(arr.len() == 1)
    assert(arr[0] == 123)

    let arr2: [pair] = __array[pair].new()
    assert(arr2.len() == 0)

    arr2.append(pair(123, 456))
    assert(arr2.len() == 1)
    assert(arr2[0].eq(pair(123, 456)))

    arr2.append(pair(789, 100))
    assert(arr2.len() == 2)
    assert(arr2[1].eq(pair(789, 100)))
