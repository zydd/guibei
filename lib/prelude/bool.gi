enum bool:
    False
    True


const True = bool.True
const False = bool.False


impl bool:
    macro __cast_from(i: i32) -> bool:
        i != 0

    func (==)(self, rhs: bool) -> bool:
        asm: (i32.eq {self} {rhs})

    func (!=)(self, rhs: bool) -> bool:
        asm: (i32.ne {self} {rhs})

    macro (&&)(self, rhs: bool) -> bool:
        if not self:
            # rhs will not be evaluated
            return False
        rhs

    macro (||)(self, rhs: bool) -> bool:
        if self:
            # rhs will not be evaluated
            return True
        rhs

    func print(self) -> ():
        bytes.print(self.repr())

    func repr(self) -> bytes:
        match self:
            case bool.True:
                return "True"
            case bool.False:
                return "False"
        ""
