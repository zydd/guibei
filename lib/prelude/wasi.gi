:[import("wasi_snapshot_preview1", "fd_write")]
func __wasi_fd_write(fd: i32, iovs: i32, iovs_len: i32, out_nwritten: i32) -> i32


:[import("wasi_snapshot_preview1", "fd_read")]
func __wasi_fd_read(fd: i32, iovs: i32, iovs_len: i32, out_nread: i32) -> i32


func __print_n(addr: i32, count: i32) -> ():
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count})

    __wasi_fd_write(1, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))


func __read_n(addr: i32, count: i32) -> i32:
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count - 1})

    __wasi_fd_read(0, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))

    asm:
        (i32.load (global.get $__stackp))

