type File: i32

impl File:
    func open_ro(path: bytes) -> File:
        __reinterpret_cast _open(path)

    func close(self) -> ():
        let err: i32 = __wasi_fd_close(self)
        assert(err == 0)

    func read(self, count: usize) -> bytes:
        let buffer: usize = usize asm: (global.get $__stackp) + 16
        # FIXME: integral type casting
        let read_count: usize = __reinterpret_cast _read_fd(self, __reinterpret_cast buffer, __reinterpret_cast count)

        let result: bytes = bytes.repeat(read_count, 0)
        let i: usize = 0

        while i < read_count:
            result[i] = asm: (i32.load {buffer + i})
            i = i + 1

        return result

    func _open(path: bytes) -> i32:
        let stackp: usize = __push(path)
        asm:
            (i32.store offset=0 (global.get $__stackp) {i32 (-1)})
            (i32.store offset=4 (global.get $__stackp) {stackp})
            (i32.store offset=8 (global.get $__stackp) {path.len()})

        let o_read: i64 = 0x02
        let o_write: i64 = 0x40

        let err: i32 = __wasi_path_open(
            3,
            0,
            __reinterpret_cast stackp,
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

    func _read_fd(fd: i32, addr: i32, count: i32) -> i32:
        asm:
            (i32.store offset=0 (global.get $__stackp) {i32 0})
            (i32.store offset=4 (global.get $__stackp) {addr})
            (i32.store offset=8 (global.get $__stackp) {count - 1})

        let err: i32 = __wasi_fd_read(fd, i32 asm: (global.get $__stackp) + 4, 1, asm: (global.get $__stackp))

        asm:
            (i32.load (global.get $__stackp))
