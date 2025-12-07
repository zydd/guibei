type pair2[T, U]: (T, U)


# type array[T]

# impl[T] array[T]:
#     macro __type_declaration() -> ():
#         asm:
#             (array (mut {T.__type_reference}))

#     macro __type_reference() -> ():
#         asm:
#             (ref {Self.__asm_type})

#     macro len(self: Self) -> i32:
#         asm:
#             (array.len {self})


func main() -> ():
    let val: i32 = 3

