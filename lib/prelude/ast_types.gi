asm:
    (export "memory" (memory $memory))
    (export "_start" (func $root.main))
    (memory $memory 16)
    (global $__stackp (mut i32) (i32.const 0))
    (type $vtd (array (mut funcref)))
    (global (ref $vtd) (array.new_default $vtd (i32.const 13)))
    (type $__enum (sub (struct (field i32))))


type __enum_discr: __integral[i32, i32, array.get]
impl __enum_discr:
    macro __from_literal(i: __int) -> Self:
        asm: (i32.const {i})

