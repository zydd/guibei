:[import("wasi_snapshot_preview1", "fd_write")]
func __wasi_fd_write(fd: i32, iovs: i32, iovs_len: i32, out_nwritten: i32) -> i32


:[import("wasi_snapshot_preview1", "fd_read")]
func __wasi_fd_read(fd: i32, iovs: i32, iovs_len: i32, out_nread: i32) -> i32


:[import("wasi_snapshot_preview1", "fd_close")]
func __wasi_fd_close(fd: i32) -> i32


:[import("wasi_snapshot_preview1", "path_open")]
func __wasi_path_open(
    dirfd: i32,
    dirflags: i32,
    path: i32,
    path_len: i32,
    oflags: i32,
    fs_rights_base: i64,
    fs_rights_inheriting: i64,
    fdflags: i32,
    opened_fd: i32
) -> i32


func __push(string: bytes) -> usize:
    let stackp: usize = asm: (global.get $__stackp)
    let i: usize = 0

    while i < string.len():
        asm: (i32.store8 {stackp + i} {string[i]})
        i = i + 1

    # Align to 4
    asm: (global.set $__stackp {((stackp + string.len()) & 0xfffffffc) + 4})

    stackp


func __print(string: bytes) -> i32:
    __write_fd(1, string)


func __write_fd(fd: i32, string: bytes) -> i32:
    let stackp: usize = __push(string)

    asm:
        (i32.store offset=4 (global.get $__stackp) {stackp})
        (i32.store offset=8 (global.get $__stackp) {string.len()})

    let err: i32 = __wasi_fd_write(fd, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))
    assert(err == 0)

    # Pop
    asm: (global.set $__stackp {stackp})

    return err


func __print_n(addr: i32, count: i32) -> ():
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count})

    __wasi_fd_write(1, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))

