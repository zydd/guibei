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
type i8: __native_type<i8>
type int: __native_type<i32>
type pair: (i32, i32)
type bytes: i8[]


func one_one() -> pair:
    pair(1, 1)


func repeat(byte: int, count: i32) -> bytes:
    bytes(byte, count)


func addi32(a: i32, b: i32) -> i32:
    asm:
        (i32.add (local.get $a) (local.get $b))


func printbn(arr: bytes):
    let i: i32 = 0
    let len: i32
    asm:
        (local.set $len (array.len (local.get $arr)))
        (block $break
            (loop $copy
                (br_if $break (i32.ge_u (local.get $i) (local.get $len)))
                (i32.store8
                    (local.get $i)
                    (array.get_u $bytes (local.get $arr) (local.get $i))
                )
                (local.set $i (i32.add (local.get $i) (i32.const 1)))
                (br $copy)
            )
        )
    printn(0, len)


func printn(addr: i32, count: i32):
    asm:
        (i32.store offset=4 (global.get $__stackp) (local.get $addr))
        (i32.store offset=8 (global.get $__stackp) (local.get $count))

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
        (i32.store offset=4 (global.get $__stackp) (local.get $addr))
        (i32.store offset=8 (global.get $__stackp) (i32.sub (local.get $count) (i32.const 1)))

        (call $__wasi_fd_read
            (i32.const 0)
            (i32.add (global.get $__stackp) (i32.const 4))
            (i32.const 1)
            (global.get $__stackp)
        )
        (drop)
        (local.tee $read_count (i32.load (global.get $__stackp)))
        (i32.store (i32.add (local.get $addr) (local.get $read_count)) (i32.const 0))


asm: (data (i32.const 0) "Hello World!\n")


func main():
    printbn(repeat(97, 10))
    printbn(repeat(10, 1))
    printbn(bytes(98, 10))
    let newlines: bytes = repeat(10, 2)
    printbn(newlines)
