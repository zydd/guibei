enum bool:
    False
    True


const True = bool.True
const False = bool.False


impl bool:
    func (==)(self, rhs: Self) -> bool:
        asm: (i32.eq {self} {rhs})

    func (!=)(self, rhs: Self) -> bool:
        asm: (i32.ne {self} {rhs})

    func (&&)(self, rhs: Self) -> Self:
        asm: (i32.and {self} {rhs})

    func (||)(self, rhs: Self) -> Self:
        asm: (i32.or {self} {rhs})

    # func print(self) -> ():
    #     match self:
    #         case bool.True:
    #             bytes.print("True")
    #         case bool.False:
    #             bytes.print("False")
