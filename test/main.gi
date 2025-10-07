asm:
    (import "wasi_snapshot_preview1" "fd_write"
        (func $__wasi_fd_write (type $__wasi_fd_write_t)))

    (type $__wasi_fd_write_t
        (func
            (param $fd i32)
            (param $iovs i32)
            (param $iovs_len i32)
            (param $out_nwritten i32)
            (result i32)))

    (import "wasi_snapshot_preview1" "fd_read"
        (func $__wasi_fd_read (type $__wasi_fd_read_t)))

    (type $__wasi_fd_read_t
        (func
            (param $fd i32)
            (param $iovs i32)
            (param $iovs_len i32)
            (param $out_nread i32)
            (result i32)))

asm:
    (export "memory" (memory $memory))
    (export "_start" (func $main))
    (memory $memory 1)
    (global $__stackp (mut i32) (i32.const 1024))


type i32: __native_type<i32>
type i64: __native_type<i64>
type i8: __native_type<i8>
type bytes: i8[]
type pair: (i32, i32)
type mat2x2: (pair, pair)


func one_one() -> pair:
    pair(1, 1)


func repeat(byte: i32, count: i32) -> bytes:
    bytes(byte, count)


func (+)(a: i32, b: i32) -> i32:
    return asm: (i32.add {a} {b})
    asm: (i32.sub {a} {b})


func (-)(a: i32, b: i32) -> i32:
    asm: (i32.sub {a} {b})


func (<)(a: i32, b: i32) -> i32:
    asm: (i32.lt_s {a} {b})


func print_bytes(arr: bytes):
    let i: i32 = 0
    let len: i32 = asm: (array.len (local.get $arr))
    while i < len:
        asm: (i32.store8 {i} {arr[i]})
        i = i + 1

    printn(0, len)


func printn(addr: i32, count: i32):
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count})

        (call $__wasi_fd_write
            (i32.const 1)
            (i32.add (global.get $__stackp) (i32.const 4))
            (i32.const 1)
            (global.get $__stackp)
        )
        (drop)


func readn(addr: i32, count: i32) -> i32:
    let read_count: i32
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count - 1})

        (call $__wasi_fd_read
            (i32.const 0)
            (i32.add (global.get $__stackp) (i32.const 4))
            (i32.const 1)
            (global.get $__stackp)
        )
        (drop)
        (i32.load (global.get $__stackp))


asm: (data (i32.const 0) "Hello World!\n")


func main():
    let txt: pair = pair(97, 97 + 1)
    txt.0
    print_bytes(repeat(txt.0, 10))
    print_bytes(repeat(10, one_one().1))
    print_bytes(bytes(txt.1, 10))
    let newlines: bytes = repeat(10, 2)
    let first: i32 = newlines[0]
    print_bytes(newlines)
