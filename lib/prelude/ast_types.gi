asm:
    (export "memory" (memory $memory))
    (export "_start" (func $root.main))
    (memory $memory 1)
    (global $__stackp (mut i32) (i32.const 1024))
    (type $vtd (array (mut funcref)))
    (global (ref $vtd) (array.new_default $vtd (i32.const 13)))
    (type $__enum (sub (struct (field i32))))
    (type $__string_literal (array (mut i8)))


type __array_index: i32


type __enum_discr: i32
impl __enum_discr:
    macro __from_literal(i: __int) -> Self:
        asm: (i32.const {i})

