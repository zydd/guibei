type pair2[T, U]: (T, U)


type array[T]

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

#     func is_empty(self: Self) -> i32:
#         let res: i32 = 0
#         if Self.len(self) == 0:
#             res = 1
#         else:
#             res = 0
#         return res


func main() -> ():
    let val: i32 = 1

