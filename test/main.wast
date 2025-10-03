(module
    (import
        "wasi_snapshot_preview1"
        "fd_write"
        (func $__wasi_fd_write (type $__wasi_fd_write_t))
    )
    (type
        $__wasi_fd_write_t
        (func
            (param $fd i32)
            (param $iovs i32)
            (param $iovs_len i32)
            (param $out_nwritten i32)
            (result i32)
        )
    )
    (import
        "wasi_snapshot_preview1"
        "fd_read"
        (func $__wasi_fd_read (type $__wasi_fd_read_t))
    )
    (type
        $__wasi_fd_read_t
        (func
            (param $fd i32)
            (param $iovs i32)
            (param $iovs_len i32)
            (param $out_nread i32)
            (result i32)
        )
    )
    (global $__stackp (mut i32) (i32.const 1024))
    (export "memory" (memory $memory))
    (export "_start" (func $main))
    (memory $memory 1)
    (type $pair (struct (field i32) (field i32)))
    (type $bytes (array (mut i32)))
    (func
        $addi32
        (param $a i32)
        (param $b i32)
        (result i32)
        (i32.add (local.get $a) (local.get $b))
    )
    (func
        $printn
        (param $addr i32)
        (param $count i32)
        (i32.store offset=4 (global.get $__stackp) (local.get $addr))
        (i32.store offset=8 (global.get $__stackp) (local.get $count))
        (call
            $__wasi_fd_write
            (i32.const 1)
            (i32.add (global.get $__stackp) (i32.const 4))
            (i32.const 1)
            (global.get $__stackp)
        )
        (drop)
    )
    (func
        $readn
        (param $addr i32)
        (param $count i32)
        (result i32)
        (local $read_count i32)
        (i32.store offset=4 (global.get $__stackp) (local.get $addr))
        (i32.store
            offset=8
            (global.get $__stackp)
            (i32.sub (local.get $count) (i32.const 1))
        )
        (call
            $__wasi_fd_read
            (i32.const 0)
            (i32.add (global.get $__stackp) (i32.const 4))
            (i32.const 1)
            (global.get $__stackp)
        )
        (drop)
        (local.tee $read_count (i32.load (global.get $__stackp)))
        (i32.store (i32.add (local.get $addr) (local.get $read_count)) (i32.const 0))
    )
    (data (i32.const 0) "Hello World!\n")
    (func
        $main
        (local $read_count i32)
        (call $readn (i32.const 0) (i32.const 1024))
        (local.set $read_count)
        (call $printn (i32.const 0) (local.get $read_count))
    )
)
