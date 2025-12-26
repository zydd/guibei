:[import("wasi_snapshot_preview1", "fd_write")]
func __wasi_fd_write(fd: i32, iovs: i32, iovs_len: i32, out_nwritten: i32) -> i32


:[import("wasi_snapshot_preview1", "fd_read")]
func __wasi_fd_read(fd: i32, iovs: i32, iovs_len: i32, out_nread: i32) -> i32


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


func __open(path: bytes) -> i32:
    let stackp: i32 = __push(path)
    asm:
        (i32.store offset=0 (global.get $__stackp) {i32 (-1)})
        (i32.store offset=4 (global.get $__stackp) {stackp})
        (i32.store offset=8 (global.get $__stackp) {path.len()})

    let o_read: i64 = 0x02
    let o_write: i64 = 0x40

    let err: i32 = __wasi_path_open(
        3,
        0,
        stackp,
        __reinterpret_cast path.len(),
        0,
        o_read,
        0,
        0,
        i32 asm: (global.get $__stackp)
    )


    let fd: i32 = asm: (i32.load (global.get $__stackp))

    # Pop
    asm: (global.set $__stackp {stackp})

    return fd

func __push(string: bytes) -> i32:
    let stackp: usize = asm: (global.get $__stackp)
    let i: usize = 0
    let len: usize = asm: (array.len (local.get $string))

    while i < len:
        asm: (i32.store8 {stackp + i} {string[i]})
        i = i + 1

    # Align to 4
    asm: (global.set $__stackp {((stackp + string.len()) & 0xfffffffc) + 4})

    # FIXME: integral type casting
    __reinterpret_cast stackp


func __print(string: bytes) -> i32:
    __print_fd(1, string)




func __print_fd(fd: i32, string: bytes) -> i32:
    let stackp: i32 = __push(string)

    asm:
        (i32.store offset=4 (global.get $__stackp) {stackp})
        (i32.store offset=8 (global.get $__stackp) {string.len()})

    let err: i32 = __wasi_fd_write(fd, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))

    # Pop
    asm: (global.set $__stackp {stackp})

    return err


func __print_n(addr: i32, count: i32) -> ():
    asm:
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count})

    __wasi_fd_write(1, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))


func __read_fd(fd: i32, count: usize) -> bytes:
    let buffer: usize = usize asm: (global.get $__stackp) + 16
    # FIXME: integral type casting
    let read_count: usize = __reinterpret_cast __read_fd_n(fd, __reinterpret_cast buffer, __reinterpret_cast count)

    let result: bytes = bytes.repeat(read_count, "\0")
    let i: usize = 0

    while i < read_count:
        result[i] = asm: (i32.load {buffer + i})
        i = i + 1
    return result


func __read_fd_n(fd: i32, addr: i32, count: i32) -> i32:
    asm:
        (i32.store offset=0 (global.get $__stackp) {i32 0})
        (i32.store offset=4 (global.get $__stackp) {addr})
        (i32.store offset=8 (global.get $__stackp) {count - 1})

    let err: i32 = __wasi_fd_read(fd, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))

    # bytes.print("err:")
    # err.print()
    # bytes.print("\n")

    asm:
        (i32.load (global.get $__stackp))


func __read_n(addr: i32, count: i32) -> i32:
    __read_fd_n(0, addr, count)

