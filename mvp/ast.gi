type ParseInfo: (line: usize, column: usize, len: usize)


enum TypeExpr:
    Name(info: ParseInfo, name: str)
    Tuple(info: ParseInfo, fields: vec<TupleField>)
    Array(info: ParseInfo, element_type: TypeExpr)
    Native(info: ParseInfo, name: str, packed: str, signed: bool)
    FunctionType(info: ParseInfo, args: Tuple, ret: Option<TypeExpr>)
    Void(info: ParseInfo)
    Unspecified(info: ParseInfo)


enum Expr:
    Module(info: ParseInfo, body: vec<Expr>)

    Name(info: ParseInfo, name: str)
    TypeExpr(info: ParseInfo, TypeExpr)
    Placeholder(info: ParseInfo)

    IntLiteral(info: ParseInfo, value: str)
    StringLiteral(info: ParseInfo, value: str)
    Tuple(info: ParseInfo, fields: vec<TupleField>)

    GetItem(info: ParseInfo, expr: Expr, idx: Expr)
    GetAttr(info: ParseInfo, expr: Expr, attr: str)

    Call(info: ParseInfo, expr: Expr, arg: Expr)
    Cast(info: ParseInfo, expr: Expr, arg: Expr)

    Asm(info: ParseInfo, vec<WasmExpr>)
    FunctionDef(info: ParseInfo, name: str, args: Tuple, ret: Option<TypeExpr>, body: vec<Expr>)
    TypeImpl(info: ParseInfo, name: str, body: vec<Expr>)
    EnumDef(info: ParseInfo, name: str, body: vec<EnumValue>)

    VarDecl(info: ParseInfo, name: str, TypeExpr: TypeExpr, init: Expr)
    Assignment(info: ParseInfo, lvalue: Expr, expr: Expr)
    IfElse(info: ParseInfo, condition: Expr, body_then: vec<Expr>, body_else: vec<Expr>)
    While(info: ParseInfo, condition: Expr, body: vec<Expr>)
    Match(info: ParseInfo, expr: Expr, cases: vec<MatchCase>)
    FunctionReturn(info: ParseInfo, expr: Expr)


type TupleField: (info: ParseInfo, name: Option<str>, value: Expr)
type EnumValue: (info: ParseInfo, name: str, Option<TypeExpr.Tuple>)


enum WasmExpr:
    Term(info: ParseInfo, str)
    Expr(info: ParseInfo, Expr)
    WasmExpr(info: ParseInfo, vec<WasmExpr>)
