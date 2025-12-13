from . import ir
from . import traverse_ir


def wasm_repr_indented(expr: list[str | int | list], level=0) -> str:
    indent = "    " * level
    if len(expr) == 1 and not isinstance(expr[0], list):
        return f"{indent}({expr[0]})"
    else:
        terms = []
        if expr:
            terms.append("\n" + wasm_repr_indented(expr[0], level + 1) if isinstance(expr[0], list) else str(expr[0]))
            n = 1
            if len(expr) > 1 and expr[0] != "elem" and isinstance(expr[1], str) and expr[1].startswith("$"):
                terms[0] += " " + expr[1]
                n += 1
            for term in expr[n:]:
                terms.append(
                    wasm_repr_indented(term, level + 1) if isinstance(term, list) else f"{'    ' * (level + 1)}{term}"
                )
        inner = "\n".join(terms)
        if len(inner) < 80:
            return indent + _wasm_repr_flat(expr)
        return f"{indent}({inner}\n{indent})"


def _wasm_repr_flat(expr):
    format = lambda term: _wasm_repr_flat(term) if isinstance(term, list) else str(term)
    return f"({' '.join(map(format, expr))})"


def type_reference(node: ir.Node) -> list:
    match node:
        case ir.TypeDef():
            primitive = node.primitive()
            match primitive:
                case ir.TypeDef() if "__type_reference" in primitive.scope.attrs:
                    type_ref_macro = primitive.scope.attrs["__type_reference"]
                    assert isinstance(type_ref_macro, ir.MacroDef)
                    return translate_wasm(type_ref_macro.func.scope)

                case ir.TupleType() | ir.ArrayType() | ir.EnumType():
                    return [["ref", f"${node.name}"]]

                case _:
                    raise NotImplementedError(type(primitive))

        case ir.TypeRef():
            return type_reference(node.type_)

        case _:
            raise NotImplementedError(type(node))

    raise NotImplementedError


def type_packed(node: ir.Node) -> list:
    match node:
        case ir.TypeDef():
            try:
                type_ref_macro = node.scope.attrs["__type_packed"]
                assert isinstance(type_ref_macro, ir.MacroDef)
                return translate_wasm(type_ref_macro.func.scope)
            except KeyError:
                return type_reference(node)

        case ir.TypeRef():
            return type_packed(node.type_)

        case _:
            raise NotImplementedError(type(node))


def type_declaration(node: ir.Node) -> list:
    decl: list

    match node:
        case ir.EnumType():
            decl = [["type", f"${node.name}", ["sub $__enum (struct (field", *type_reference(node.discr_type), "))"]]]

            for attr in node.scope.attrs.values():
                decl.extend(type_declaration(attr))

            return decl

        case ir.EnumValueType():
            assert isinstance(node.super_, ir.TypeRef), node.super_
            assert isinstance(node.super_.type_, ir.EnumType)

            fields = [["field", ["mut", *type_reference(type_)]] for type_ in node.field_types]
            fields.insert(0, ["field", *type_reference(node.super_.type_.discr_type)])

            return [["type", f"${node.name}", ["sub", f"${node.super_.name}", ["struct", *fields]]]]

        case ir.TypeDef():
            primitive = node.primitive()
            if isinstance(primitive, ir.TypeDef):
                try:
                    type_ref_macro = primitive.scope.attrs["__type_declaration"]
                    assert isinstance(type_ref_macro, ir.MacroDef)
                    decl = translate_wasm(type_ref_macro.func.scope)
                except KeyError:
                    if primitive.super_ is None:
                        return []
            else:
                decl = type_declaration(primitive)

                assert node.super_
                if isinstance(node.super_.primitive(), ir.TupleType):
                    if isinstance(node.super_, ir.TypeRef):
                        decl = [["sub", f"${node.super_.name}", *decl]]
                    else:
                        decl = [["sub", *decl]]

            return [["type", f"${node.name}", *decl]]

        case ir.ArrayType():
            return [["array", ["mut", *type_packed(node.element_type)]]]

        case ir.TupleType():
            fields = [["field", ["mut", *type_reference(type_)]] for type_ in node.field_types]
            return [["struct", *fields]]

        case ir.TemplateDef():
            decl = []
            for inst in node.instances.values():
                decl.extend(type_declaration(inst))
            return decl

        case (
            ir.TypeRef()
            | ir.FunctionDef()
            | ir.FunctionRef()
            | ir.AsmType()
            | ir.MacroDef()
            | ir.TemplateArg()
            | ir.OverloadedFunction()
            | ir.ConstDecl()
            | ir.AstType()
        ):
            return []

    raise NotImplementedError(type(node))


def translate_wasm(node: ir.Node) -> list[str | int | list]:
    match node:
        case ir.Module():
            terms: list = ["module"]

            for attr in node.scope.attrs.values():
                annotations = getattr(attr, "annotations", None)
                if annotations:
                    assert isinstance(attr, ir.FunctionDef)
                    terms.append(
                        [
                            "func",
                            f"${attr.name}",
                            [
                                "import",
                                f'"{annotations[0].arg.field_values[0].value}"',
                                f'"{annotations[0].arg.field_values[1].value}"',
                            ],
                            ["type", f"${attr.name}.__type"],
                        ]
                    )

            for expr in node.asm:
                terms.extend(translate_wasm(expr))

            for attr in node.scope.attrs.values():
                terms.extend(type_declaration(attr))

            for attr in node.scope.attrs.values():
                terms.extend(translate_wasm(attr))

            return terms

        case ir.IntLiteral():
            return [node.value]

        case ir.AsmType():
            return [node.name]

        case ir.WasmExpr():
            terms = []
            for term in node.terms:
                if isinstance(term, ir.WasmExpr):
                    terms.append(translate_wasm(term))
                elif isinstance(term, ir.Node):
                    terms.extend(translate_wasm(term))
                else:
                    terms.append(term)
            return terms

        case ir.TypeDef():
            return translate_wasm(node.scope)

        case ir.TemplateDef():
            terms = []
            for attr in node.instances.values():
                terms.extend(translate_wasm(attr))
            return terms

        case ir.FunctionDef():
            decls: list = [["param", f"${arg.name}", *type_reference(arg.type_)] for arg in node.type_.args]
            if not isinstance(node.type_.ret_type, ir.VoidType):
                decls.append(["result", *type_reference(node.type_.ret_type)])

            # TODO
            if hasattr(node, "annotations"):
                return [["type", f"${node.name}.__type", ["func", *decls]]]

            body = translate_wasm(node.scope)

            return [
                ["type", f"${node.name}.__type", ["func", *decls]],
                ["func", f"${node.name}", ["type", f"${node.name}.__type"], *decls, *body],
            ]

        case ir.FunctionReturn():
            return [["return", *translate_wasm(node.expr)]]

        case ir.Scope():
            terms = []
            for attr_name, expr in node.attrs.items():
                # if attr_name.startswith("__"):
                #     continue

                match expr:
                    case ir.VarDecl() | ir.FunctionDef():
                        terms.extend(translate_wasm(expr))

                    case (
                        ir.TypeRef()
                        | ir.VarRef()
                        | ir.ArgRef()
                        | ir.AsmType()
                        | ir.EnumValueType()
                        | ir.MacroDef()
                        | ir.TemplateArgRef()
                        | ir.SelfType()
                        | ir.ConstDecl()
                    ):
                        pass

                    case _:
                        raise NotImplementedError(type(expr))
            for expr in node.body:
                terms.extend(translate_wasm(expr))
            return terms

        case ir.VarDecl():
            return [["local", f"${node.name}", *type_reference(node.type_)]]

        case ir.VarRef():
            return [["local.get", f"${node.var.name}"]]

        case ir.ArgRef():
            return [["local.get", f"${node.arg.name}"]]

        case ir.Asm():
            assert isinstance(node.terms, ir.WasmExpr)
            return translate_wasm(node.terms)

        case ir.IfElse():
            else_block = [["else", *translate_wasm(node.scope_else)]] if node.scope_else.body else []
            return [["if", *translate_wasm(node.condition), ["then", *translate_wasm(node.scope_then)], *else_block]]

        case ir.Block():
            result = [["result", *type_reference(node.type_)]] if not isinstance(node.type_, ir.VoidType) else []
            return [["block", f"${node.name}", *result, *translate_wasm(node.scope)]]

        case ir.Break():
            return [["br", f"${node.block_name}", *translate_wasm(node.expr)]]

        case ir.Loop():
            body = translate_wasm(node.scope)
            assert node.post_condition is None
            id = 0
            return [
                [
                    "block",
                    f"${node.scope.name}.__block",
                    [
                        "loop",
                        f"${node.scope.name}.__loop",
                        [
                            "br_if",
                            f"${node.scope.name}.__block",
                            ["i32.eqz", *translate_wasm(node.pre_condition)],
                        ],
                        *body,
                        ["br", f"${node.scope.name}.__loop"],
                    ],
                ]
            ]

        case ir.SetLocal():
            return [["local.set", f"${node.var.var.name}", *translate_wasm(node.expr)]]

        case ir.SetItem():
            assert isinstance(node.expr.type_, ir.TypeRef)
            assert isinstance(node.expr.type_.type_, ir.TypeDef)
            return [
                [
                    "array.set",
                    f"${node.expr.type_.type_.name}",
                    *translate_wasm(node.expr),
                    *translate_wasm(node.idx),
                    *translate_wasm(node.value),
                ]
            ]

        case ir.FunctionCall():
            return [["call", f"${node.func.func.name}"] + [term for arg in node.args for term in translate_wasm(arg)]]

        case ir.GetTupleItem():
            assert isinstance(node.expr.type_, ir.TypeRef)
            assert isinstance(node.expr.type_.type_, ir.TypeDef)
            return [["struct.get", f"${node.expr.type_.type_.name}", node.idx, *translate_wasm(node.expr)]]

        case ir.SetTupleItem():
            assert isinstance(node.expr.type_, ir.TypeRef)
            assert isinstance(node.expr.type_.type_, ir.TypeDef)
            return [
                [
                    "struct.set",
                    f"${node.expr.type_.type_.name}",
                    node.idx,
                    *translate_wasm(node.expr),
                    *translate_wasm(node.value),
                ]
            ]

        case ir.GetItem():
            elem_primitive = node.expr.type_.primitive().element_type.primitive()
            assert isinstance(node.expr.type_, ir.TypeRef)
            assert isinstance(node.expr.type_.type_, ir.TypeDef)
            match elem_primitive:
                case ir.TypeDef():
                    getter = elem_primitive.scope.attrs["__array_unpack"]
                    assert isinstance(getter, ir.MacroDef)
                    inlined = traverse_ir.inline(getter, getter.func.scope, [node.expr, node.idx])
                    return translate_wasm(inlined)
                case ir.TupleType():
                    return [
                        [
                            "array.get",
                            f"${node.expr.type_.type_.name}",
                            *translate_wasm(node.expr),
                            *translate_wasm(node.idx),
                        ]
                    ]
                case _:
                    breakpoint()
                    raise NotImplementedError(elem_primitive)

        case ir.StringLiteral():
            assert isinstance(node.type_, ir.AstType)
            return [
                [
                    f"local.tee ${node.temp_var.var.name}",
                    [f"array.new_default ${node.type_.name}", f"(i32.const {len(node.value)})"],
                ],
                *(
                    [
                        f"array.set ${node.type_.name} (local.get ${node.temp_var.var.name}) (i32.const {i}) (i32.const {byte})"
                    ]
                    for i, byte in enumerate(node.value.encode("ascii"))
                ),
            ]

        case ir.Drop():
            return [["drop", *translate_wasm(node.expr)]]

        case ir.TupleInst():
            assert isinstance(node.type_, ir.TypeRef)
            assert isinstance(node.type_.type_, ir.TypeDef)

            args = []
            for arg in node.args:
                args.extend(translate_wasm(arg))

            return [["struct.new", f"${node.type_.type_.name}", *args]]

        case ir.MatchEnum():
            assert isinstance(node.match_expr.expr, ir.Expr)
            enum_type = node.match_expr.expr.type_.primitive()
            enum_values = [val for val in enum_type.scope.attrs.values() if isinstance(val, ir.EnumValueType)]
            enum_values.sort(key=lambda v: v.discr)

            cases: list = [None] * len(enum_values)
            for case in node.cases:
                assert isinstance(case.enum, ir.TypeRef)
                assert isinstance(case.enum.type_, ir.EnumValueType)
                cases[case.enum.type_.discr] = case

            block_names = [f"${case.scope.name}" for case in cases]

            # TODO
            default_case = ["unreachable"]

            terms = [
                [
                    "br_table",
                    *block_names,
                    ["struct.get", "$__enum", 0, ["local.get", f"${node.match_expr.var.name}"]],
                ],
                *default_case,
            ]
            for val, case in zip(reversed(enum_values), reversed(cases)):
                assert isinstance(case, ir.MatchCaseEnum)
                assert isinstance(case.enum, ir.TypeRef)
                assert isinstance(case.enum.type_, ir.EnumValueType)
                args = []
                for i, matched_field in enumerate(case.args):
                    if isinstance(matched_field, ir.VarRef):
                        args.append(
                            [
                                "local.set",
                                f"${matched_field.var.name}",
                                [
                                    "struct.get",
                                    f"${case.enum.type_.name}",
                                    i,
                                    [
                                        "ref.cast",
                                        f"(ref ${case.enum.type_.name})",
                                        "local.get",
                                        f"${node.match_expr.var.name}",
                                    ],
                                ],
                            ]
                        )
                terms = [
                    ["block", f"${case.scope.name}", *terms],
                    *args,
                    *translate_wasm(case.scope),
                    ["br", f"${node.scope.name}"],
                ]

            terms = ["block", f"${node.scope.name}", *terms]

            return [*translate_wasm(node.match_expr), terms]

        case ir.MacroDef() | ir.VoidExpr() | ir.FunctionRef() | ir.OverloadedFunction() | ir.ConstDecl():
            return []

        case ir.ReinterpretCast():
            return translate_wasm(node.expr)

    return [str(node)]
    raise NotImplementedError(node)
