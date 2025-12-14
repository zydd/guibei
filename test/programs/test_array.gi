func main() -> ():
    let arr: [i32] = __array[i32].new()
    assert(arr.len() == 0)

    arr.append(123)
    assert(arr.len() == 1)
    assert(arr.at(0) == 123)

    let arr2: [pair] = __array[pair].new()
    assert(arr2.len() == 0)

    arr2.append((123, 456))
    assert(arr2.len() == 1)
    assert(arr2.at(0).eq((123, 456)))

    arr2.append((789, 100))
    assert(arr2.len() == 2)
    assert(arr2.at(1).eq((789, 100)))
