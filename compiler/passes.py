from compiler import ast
from compiler import ir
from compiler import traverse_ast
from compiler import traverse_ir


def write_tree(filename):
    import pprint

    def write(node: ir.Node):
        with open(filename, "w") as f:
            pprint.pprint(node, stream=f)

        return node

    return write


def register_toplevel_decls(node: ast.Node, module: ir.Module):
    match node:
        case ast.Module():
            traverse_ast.traverse(register_toplevel_decls, node, module)
        case ast.TypeDef():
            module.scope.register_type(
                node.name,
                ir.TypeDef(
                    node.info,
                    ir.UntranslatedType(node.super_) if node.super_ else None,
                    node.name,
                    ir.Scope(module.scope, node.name),
                ),
            )
        case ast.EnumType():
            enum_type = ir.EnumType.translate(node, module.scope)
            module.scope.register_type(node.name, enum_type)
            for i, val in enumerate(node.values):
                enum_type.scope.register_type(val.name, ir.EnumValueType.translate(enum_type, i, val))
        case ast.TemplateDef():
            module.scope.register_type(node.name, ir.TemplateDef.translate(node, module.scope))
        case ast.FunctionDef():
            fn_def = ir.FunctionDef.translate(node, module.scope)
            if hasattr(node, "annotations"):
                fn_def.annotations = node.annotations
            module.scope.add_method(node.name, fn_def)
        case ast.MacroDef():
            module.scope.add_method(node.name, ir.MacroDef.translate(node, module.scope))
        case ast.Asm():
            module.add_asm(ir.Untranslated(node))
        case _:
            return node


def register_toplevel_methods(node: ast.Node, module: ir.Module):
    match node:
        case ast.Module():
            traverse_ast.traverse(register_toplevel_methods, node, module)
        case ast.TypeImpl():
            assert isinstance(node.type_, ast.TypeIdentifier)
            type_ = module.scope.lookup_type(node.type_.name)
            assert isinstance(type_, ir.TypeDef)
            for method in node.methods:
                match method:
                    case ast.FunctionDef():
                        type_.scope.add_method(method.name, ir.FunctionDef.translate(method, type_.scope))
                    case ast.MacroDef():
                        type_.scope.add_method(method.name, ir.MacroDef.translate(method, type_.scope))
                    case _:
                        raise NotImplementedError(type(method))

        case ast.TemplateTypeImpl():
            assert isinstance(node.type_, ast.TemplateInst)
            template = module.scope.lookup(node.type_.name.name)
            assert isinstance(template, ir.TemplateDef)
            assert [arg.name for arg in node.args] == [arg.name for arg in node.type_.args]  # type:ignore
            assert [arg.name for arg in node.args] == [arg.name for arg in template.args]  # type:ignore

            for method in node.methods:
                match method:
                    case ast.FunctionDef():
                        template.scope.add_method(method.name, ir.FunctionDef.translate(method, template.scope))
                    case ast.MacroDef():
                        template.scope.add_method(method.name, ir.MacroDef.translate(method, template.scope))
                    case _:
                        raise NotImplementedError(type(method))
        case _:
            return node


def check_unallowed_toplevel_decls(node: ast.Node, module: ir.Module):
    assert isinstance(node, ast.Module)
    assert len(node.stmts) == 0, f"{type(node.stmts[0]).__name__} not allowed as a top level declaration"


def translate_toplevel_type_decls(node: ir.Node, scope=None) -> ir.Node:
    match node:
        case ir.Module():
            node.scope.attrs = traverse_ir.traverse_dict(translate_toplevel_type_decls, node.scope.attrs, node.scope)

        case ir.UntranslatedType(ast_node=ast.ArrayType() as ast_node):
            tr_type = translate_toplevel_type_decls(ir.UntranslatedType(ast_node.element_type), scope)
            assert isinstance(tr_type, ir.Type)
            return ir.ArrayType(ast_node.info, tr_type)

        case ir.UntranslatedType(ast_node=ast.TupleType() as ast_node):
            if not ast_node.field_types:
                return ir.VoidType(ast_node.info)

            field_types = []
            field_names: list = []
            for field_type in ast_node.field_types:
                if isinstance(field_type, ast.NamedTupleElement):
                    tr_type = translate_toplevel_type_decls(ir.UntranslatedType(field_type.value), scope)
                    assert isinstance(tr_type, ir.Type)
                    field_types.append(tr_type)
                    field_names.append(field_type.name)
                else:
                    tr_type = translate_toplevel_type_decls(ir.UntranslatedType(field_type), scope)
                    assert isinstance(tr_type, ir.Type)
                    field_types.append(tr_type)
                    field_names.append(None)

            if any(x is not None for x in field_names):
                return ir.NamedTupleType(ast_node.info, field_types, field_names)
            else:
                return ir.TupleType(ast_node.info, field_types)

        case ir.UntranslatedType(ast_node=ast.TypeIdentifier() | ast.Identifier() as ast_node):
            type_: ir.Type = scope.lookup(ast_node.name)
            match type_:
                case ir.TypeDef():
                    return ir.TypeRef(node.info, type_)
                case ir.TemplateDef():
                    return ir.TemplateRef(ast_node.info, type_)
                case ir.SelfType() | ir.AstType() | ir.TypeRef() | ir.TemplateArgRef():
                    return type_
                case _:
                    raise NotImplementedError(type(type_))

        case ir.UntranslatedType(ast_node=ast.GetAttr(obj=ast.TypeIdentifier() as obj, attr=str()) as ast_node):
            type_ = scope.lookup(obj.name)
            assert isinstance(type_, ir.TypeDef)
            member = type_.scope.attrs[ast_node.attr]
            assert isinstance(member, ir.TypeDef)
            return ir.TypeRef(ast_node.info, member)

        case ir.UntranslatedType(ast_node=ast.GetItem() as template_inst):
            template = translate_toplevel_type_decls(ir.UntranslatedType(template_inst.expr), scope)
            arg = translate_toplevel_type_decls(ir.UntranslatedType(template_inst.idx), scope)
            assert isinstance(template, ir.TemplateRef)
            assert isinstance(arg, (ir.TypeRef, ir.TemplateArgRef))
            return ir.TemplateInst(node.info, template, [arg])

        case ir.UntranslatedType(ast_node=ast.TemplateInst() as ast_node):
            assert isinstance(ast_node.name, ast.TypeIdentifier)
            template = scope.lookup(ast_node.name.name)
            assert isinstance(template, ir.TemplateDef)
            args = []
            for template_arg in ast_node.args:
                assert isinstance(template_arg, ast.TypeIdentifier)
                arg = scope.lookup_type(template_arg.name)
                assert not isinstance(arg, ir.TypeRef)
                match arg:
                    case ir.TypeDef():
                        arg = ir.TypeRef(None, arg)
                    case ir.TemplateArgRef():
                        pass
                    case _:
                        raise NotImplementedError(type(arg))
                args.append(arg)
            return ir.TemplateInst(ast_node.info, ir.TemplateRef(None, template), args)

        case ir.UntranslatedType():
            return node.translate(scope)

        # case ir.TypeRef():
        #     pass

        case ir.TypeDef():
            return traverse_ir.traverse(translate_toplevel_type_decls, node, node.scope)

        case ir.TemplateDef():
            return traverse_ir.traverse(translate_toplevel_type_decls, node, node.scope)

        case ir.FunctionDef():
            tr_type = translate_toplevel_type_decls(node.type_, scope)
            assert isinstance(tr_type, ir.FunctionType)
            node.type_ = tr_type

        case _:
            return traverse_ir.traverse(translate_toplevel_type_decls, node, scope)
    return node


def check_no_untranslated_types(node: ir.Node) -> ir.Node:
    match node:
        case ir.UntranslatedType():
            raise Exception(f"Untranslated type: {node}")
        case _:
            return traverse_ir.traverse(check_no_untranslated_types, node)
    return node


def translate_function_defs(node: ir.Node, scope=None) -> ir.Node:
    match node:
        # case ir.Module():
        #     for attr in list(node.scope.attrs.values()):
        #         translate_function_defs(attr)
        #     node.asm = traverse_ir.traverse_list(translate_function_defs, node.asm)
        #     return node

        case ir.FunctionDef():
            for arg in node.type_.args:
                node.scope.add_method(arg.name, ir.ArgRef(None, arg))

            node.scope = traverse_ir.traverse(translate_function_defs, node.scope, node.scope)

            # TODO: Can't do this transformation here because we might need to drop the result of expr if the function returns void
            # if node.scope.body and isinstance(node.scope.body[-1], ir.Expr):
            #     node.scope.body[-1] = ir.FunctionReturn(None, ir.FunctionRef(None, node), node.scope.body[-1])

            return node

        case ir.Untranslated(ast_node=ast.VarDecl() as var):
            var_type = translate_toplevel_type_decls(ir.UntranslatedType(var.type_), scope)
            assert isinstance(var_type, ir.Type)
            var_decl = ir.VarDecl(var.info, var.name, var_type)
            scope.register_local(var_decl.name, var_decl)
            if var.init:
                var_init = ir.SetLocal(var.init.info, ir.VarRef(None, var_decl), ir.Untranslated(var.init))
                return translate_function_defs(var_init, scope)
            else:
                return ir.VoidType(None)

        case ir.Untranslated(ast_node=ast.Identifier() | ast.TypeIdentifier() as id):
            attr = scope.lookup(id.name)
            if isinstance(id, ast.TypeIdentifier):
                assert isinstance(attr, ir.Type)

            match attr:
                case ir.VarRef() | ir.ArgRef() | ir.TypeRef() | ir.SelfType() | ir.TemplateArgRef():
                    return attr
                case ir.VarDecl():
                    return ir.VarRef(id, attr)
                case ir.ArgDecl():
                    return ir.ArgRef(id, attr)
                case ir.FunctionDef():
                    return ir.FunctionRef(id, attr)
                case ir.TypeDef():
                    return ir.TypeRef(id, attr)
                case ir.MacroDef():
                    return ir.MacroRef(id, attr)
                case ir.TemplateDef():
                    return ir.TemplateRef(id, attr)
                case _:
                    raise NotImplementedError(type(attr))

        case ir.Untranslated(ast_node=ast.TupleExpr() as ast_node):
            if len(ast_node.field_values) == 1:
                return translate_function_defs(ir.Untranslated(ast_node.field_values[0]), scope)
            else:
                fields: list = [
                    translate_function_defs(ir.Untranslated(field), scope) for field in ast_node.field_values
                ]
                assert all(isinstance(field, ir.Expr) for field in fields)
                return ir.TupleInst(ast_node.info, ir.UnknownType(), fields)

        case ir.Untranslated(ast_node=ast.While() as while_stmt):
            pre_condition = ir.Untranslated(while_stmt.condition)
            loop_scope = ir.Scope(scope, "__while", body=[ir.Untranslated(stmt) for stmt in while_stmt.body])
            loop = ir.Loop(while_stmt.info, pre_condition, loop_scope)
            return translate_function_defs(loop, loop_scope)

        case ir.Untranslated(ast_node=ast.GetItem() as ast_node):
            expr = translate_function_defs(ir.Untranslated(ast_node.expr), scope)
            idx = translate_function_defs(ir.Untranslated(ast_node.idx), scope)
            match expr:
                case ir.Expr():
                    assert isinstance(idx, ir.Expr)
                    idx_type = scope.lookup_type("__array_index").super_

                    expr_type_prim = expr.type_.primitive()
                    if isinstance(expr_type_prim, ir.ArrayType):
                        element_type = expr_type_prim.element_type
                    else:
                        element_type = ir.UnknownType()

                    return ir.GetItem(node.info, expr, idx, idx_type, element_type)

                case ir.TemplateRef():
                    assert isinstance(idx, ir.Type)
                    return ir.TemplateInst(node.info, expr, [idx])

                case _:
                    raise NotImplementedError(type(expr))

        case ir.Untranslated(ast_node=ast.Call(callee=ast.Identifier("unary(-)"), arg=ast.IntLiteral() as value)):
            return ir.IntLiteral(value, -value.value)

        case ir.Untranslated(ast_node=ast.Call(callee=ast.Identifier("__reinterpret_cast"), arg=arg)):
            return ir.ReinterpretCast(
                node.info,
                ir.UnknownType(),
                translate_function_defs(ir.Untranslated(arg), scope),  # type:ignore[arg-type]
            )

        case ir.Scope():
            node.attrs = traverse_ir.traverse_dict(translate_function_defs, node.attrs, node)
            node.body = traverse_ir.traverse_list(translate_function_defs, node.body, node)
            return node

            # TODO: after type deduction
            # match node.lvalue:
            #     case ir.GetItem():
            #         return ir.SetItem(node.info, node.lvalue.expr, node.lvalue.idx, expr)
            #     case ir.VarRef():
            #         return ir.SetLocal(node.info, node.lvalue, node.expr)
            #     case _:
            #         raise NotImplementedError

        case ir.MatchCaseEnum():
            node.enum = translate_function_defs(node.enum, scope)
            node.args = traverse_ir.traverse_list(_translate_match_pattern, node.args, node.scope)
            node.scope = translate_function_defs(node.scope, scope)  # type:ignore[assignment]
            return node

        case ir.Untranslated():
            return translate_function_defs(node.translate(scope), scope)

        case _:
            return traverse_ir.traverse(translate_function_defs, node, scope)

    raise NotImplementedError(type(node))


def _translate_match_pattern(node: ir.Node, scope) -> ir.Node:
    match node:
        case ir.Untranslated(ast_node=ast.Placeholder() as placeholder):
            return ir.Placeholder(placeholder.info, ir.UnknownType())

        case ir.Untranslated(ast_node=ast.Identifier() as id):
            var_decl = ir.VarDecl(id.info, id.name, ir.UnknownType())
            scope.register_local(id.name, var_decl)
            return ir.VarRef(None, var_decl)

        case ir.Untranslated():
            return _translate_match_pattern(node.translate(scope), scope)

        case _:
            raise NotImplementedError


def resolve_member_access(node: ir.Node, scope=None) -> ir.Node:
    node = traverse_ir.traverse_scoped(resolve_member_access, node, scope)

    match node:
        case ir.GetAttr():
            match node.obj:
                case ir.TemplateArgRef():
                    # FIXME: translate/annotate templated methods
                    return node

                case ir.TypeRef():
                    match node.obj.type_:
                        case ir.TypeDef():
                            if node.attr == "__type_reference":
                                if isinstance(node.obj.primitive(), ir.TupleType):
                                    return ir.Asm(
                                        node.info,
                                        ir.WasmExpr(None, [["ref", f"${node.obj.type_.scope.name}"]]),
                                        ir.VoidType(None),
                                    )
                                else:
                                    type_ref_macro = node.obj.type_.scope.lookup("__type_reference")
                                    assert isinstance(type_ref_macro, ir.MacroDef)
                                    return type_ref_macro.func.scope

                            attr = node.obj.type_.scope.lookup(node.attr)
                            match attr:
                                case ir.FunctionDef():
                                    if (
                                        isinstance(node.obj.primitive(), ir.EnumValueType)
                                        and attr.type_.args[0].name == "self"
                                    ):
                                        return ir.BoundMethod(
                                            node.info,
                                            ir.UnknownType(),
                                            ir.FunctionRef(None, attr),
                                            ir.TupleInst(
                                                node.obj.info,
                                                node.obj,
                                                [ir.IntLiteral(None, node.obj.primitive().discr)],
                                            ),
                                        )
                                    else:
                                        return ir.FunctionRef(node.info, attr)
                                case ir.TypeRef():
                                    return attr
                                case ir.AsmType():
                                    return attr
                                case ir.EnumValueType():
                                    return ir.TypeRef(None, attr)
                                case ir.MacroDef():
                                    return ir.MacroRef(None, attr)
                                case _:
                                    raise NotImplementedError(type(attr))
                        case _:
                            raise NotImplementedError(type(node.obj.type_))

                case ir.Expr():
                    if isinstance(node.obj.type_, ir.TypeRef):
                        obj_type_prim = node.obj.type_.primitive()
                        if isinstance(obj_type_prim, ir.NamedTupleType) and node.attr in obj_type_prim.field_names:
                            field = obj_type_prim.field_names.index(node.attr)
                            return ir.GetTupleItem(node.info, node.obj, field, obj_type_prim.field_types[field])
                        elif isinstance(node.obj.type_.type_, ir.TypeDef):
                            method = node.obj.type_.type_.scope.lookup(node.attr)
                            assert isinstance(method, ir.FunctionDef)
                            if method.type_.args[0].name == "self":
                                return ir.BoundMethod(
                                    node.info, ir.UnknownType(), ir.FunctionRef(None, method), node.obj
                                )
                            else:
                                raise RuntimeError("Calling static method from object")
                                # return method
                        else:
                            raise NotImplementedError
                    else:
                        return node

                case ir.SelfType() | ir.TemplateInst():
                    return node

                case _:
                    # TODO
                    breakpoint()
                    return node
                    raise NotImplementedError(type(node.obj))

        case ir.GetTupleItem():
            if isinstance(node.type_, ir.UnknownType):
                assert isinstance(node.expr.type_, ir.TypeRef)

                expr_type = node.expr.type_.primitive()
                if isinstance(expr_type, ir.EnumValueType):
                    node.idx += 1
                    expr_type = expr_type.fields

                assert isinstance(expr_type, ir.TupleType)
                field_type = expr_type.field_types[node.idx]
                assert isinstance(field_type, ir.TypeRef), field_type
                node.type_ = field_type

                return node

        case ir.Assignment():
            lvalue = translate_function_defs(node.lvalue, scope)
            expr = translate_function_defs(node.expr, scope)
            assert isinstance(expr, ir.Expr)
            match lvalue:
                case ir.GetItem():
                    idx_type = scope.lookup_type("__array_index").super_
                    return ir.SetItem(node.info, lvalue.expr, lvalue.idx, idx_type, expr)

                case ir.VarRef():
                    return ir.SetLocal(node.info, lvalue, expr)

                case ir.GetAttr():
                    return node

                case ir.GetTupleItem():
                    return ir.SetTupleItem(node.info, lvalue.expr, lvalue.idx, expr)

                case _:
                    raise NotImplementedError(type(lvalue))

        case ir.Call():
            match node.callee:
                case ir.FunctionRef():
                    return ir.FunctionCall(node.info, node.callee.func.type_.ret_type, node.callee, node.args)
                case ir.BoundMethod():
                    return ir.FunctionCall(
                        node.info,
                        node.callee.func.func.type_.ret_type,
                        node.callee.func,
                        [node.callee.obj] + node.args,
                    )
                case ir.TypeRef():
                    match node.callee.primitive():
                        case ir.EnumValueType() as enum_val:
                            assert all(isinstance(arg, ir.Expr) for arg in node.args)
                            args: list = node.args
                            return ir.TupleInst(node.info, node.callee, [ir.IntLiteral(None, enum_val.discr)] + args)

                        case ir.TupleType():
                            assert all(isinstance(arg, ir.Expr) for arg in node.args)
                            tuple_args: list = node.args
                            return ir.TupleInst(node.info, node.callee, tuple_args)

                        case ir.TypeDef() as type_def:
                            assert len(node.args) == 1
                            match node.args[0]:
                                case ir.IntLiteral():
                                    from_literal = type_def.scope.lookup("__from_literal")
                                    assert isinstance(from_literal, ir.MacroDef)
                                    return ir.MacroInst(
                                        node.info,
                                        from_literal.func.type_.ret_type,
                                        ir.MacroRef(None, from_literal),
                                        node.args,
                                    )

                                case obj:
                                    assert isinstance(obj, ir.Expr)
                                    return ir.Cast(node.info, node.callee, obj)

                        case _:
                            raise NotImplementedError(node.callee)

                case ir.MacroRef():
                    return ir.MacroInst(node.info, node.callee.macro.func.type_.ret_type, node.callee, node.args)

                case ir.GetAttr() | ir.SelfType() | ir.TemplateInst():
                    return node

                case _:
                    raise NotImplementedError(type(node.callee))

    return node


def instantiate_templates(node: ir.Node, scope=None) -> ir.Node:
    node = traverse_ir.traverse_scoped(instantiate_templates, node, scope)

    match node:
        case ir.TemplateInst():
            if any(isinstance(type_, ir.TemplateArgRef) for type_ in node.args):
                return node

            assert all(isinstance(type_, ir.TypeRef) for type_ in node.args)
            type_ = traverse_ir.instantiate(node.template.template, node.args)  # type:ignore[arg-type]
            type_ = instantiate_templates(type_, scope)  # type:ignore[assignment]
            assert isinstance(type_, ir.TypeDef)
            return ir.TypeRef(None, type_)

        # case ir.TemplateDef():
        #     return node

        # case _:
        #     return traverse_ir.traverse_scoped(instantiate_templates, node, scope)

    return node


def check_no_untranslated_nodes(node: ir.Node) -> ir.Node:
    match node:
        case ir.Untranslated():
            raise Exception(f"Untranslated node: {node}")
        case _:
            return traverse_ir.traverse(check_no_untranslated_nodes, node)
    return node


def propagate_types(node: ir.Node):
    match node:
        case ir.Module():
            node.scope = propagate_types(node.scope)
            node.asm = [propagate_types(match_expr_type(asm, ir.VoidType(None))) for asm in node.asm]

        case ir.TemplateDef():
            node.instances = traverse_ir.traverse_dict(propagate_types, node.instances)
            return node

        case ir.FunctionReturn():
            node.expr = propagate_types(match_expr_type(node.expr, node.func.func.type_.ret_type))

        case ir.FunctionCall():
            func_args = node.func.func.type_.args
            assert len(node.args) == len(func_args)
            node.args = [
                propagate_types(match_expr_type(arg, arg_decl.type_)) for arg, arg_decl in zip(node.args, func_args)
            ]

        case ir.MacroDef():
            if node.name in ["__type_declaration", "__type_reference", "__type_packed"]:
                assert len(node.func.type_.args) == 0
                assert isinstance(node.func.type_.ret_type, ir.VoidType)
                node.func = propagate_types(node.func)
                return node
            else:
                node.func = propagate_types(node.func)

        case ir.MacroInst():
            func_args = node.macro.macro.func.type_.args
            assert len(node.args) == len(func_args)
            node.args = [
                propagate_types(match_expr_type(arg, arg_decl.type_)) for arg, arg_decl in zip(node.args, func_args)
            ]

        case ir.TupleInst():
            assert isinstance(node.type_, ir.TypeRef)
            match node.type_.primitive():
                case ir.TupleType() as tup:
                    assert len(node.args) == len(tup.field_types)
                    node.args = [
                        propagate_types(match_expr_type(arg, field_type))
                        for arg, field_type in zip(node.args, tup.field_types)
                    ]
                case ir.EnumValueType() as enum:
                    assert len(node.args) == len(enum.fields.field_types)
                    node.args = [
                        propagate_types(match_expr_type(arg, field_type))
                        for arg, field_type in zip(node.args, enum.fields.field_types)
                    ]
                case _:
                    raise NotImplementedError(node.type_)

        case ir.FunctionDef():
            for i in range(len(node.scope.body) - 1):
                if isinstance(node.scope.body[i], ir.Asm):
                    node.scope.body[i] = propagate_types(match_expr_type(node.scope.body[i], ir.VoidType(None)))
                elif isinstance(node.scope.body[i], ir.Expr):
                    expr = propagate_types(node.scope.body[i])
                    assert not isinstance(expr.type_, ir.UnknownType)
                    node.scope.body[i] = expr if isinstance(expr.type_, ir.VoidType) else ir.Drop(expr)
                else:
                    node.scope.body[i] = propagate_types(node.scope.body[i])

            if node.scope.body:
                if isinstance(node.type_.ret_type, ir.VoidType):
                    if isinstance(node.scope.body[-1], ir.Expr):
                        if isinstance(node.scope.body[-1].type_, ir.UnknownType):
                            expr = propagate_types(match_expr_type(node.scope.body[-1], ir.VoidType(None)))
                        else:
                            expr = propagate_types(node.scope.body[-1])

                        node.scope.body[-1] = expr if isinstance(expr.type_, ir.VoidType) else ir.Drop(expr)
                    else:
                        node.scope.body[-1] = propagate_types(node.scope.body[-1])
                else:
                    match node.scope.body[-1]:
                        case ir.Expr():
                            node.scope.body[-1] = propagate_types(
                                match_expr_type(node.scope.body[-1], node.type_.ret_type)
                            )
                        case ir.FunctionReturn():
                            node.scope.body[-1] = propagate_types(node.scope.body[-1])
                        case _:
                            # TODO: check if statements always return
                            node.scope.body[-1] = propagate_types(node.scope.body[-1])
                            # raise Exception(f"Unexpected node type in function body: {type(node.scope.body[-1])}")

        case ir.Block():
            assert not (node.scope.attrs)
            if node.scope.body:
                if isinstance(node.type_, ir.VoidType):
                    if isinstance(node.scope.body[-1], ir.Expr):
                        if isinstance(node.scope.body[-1].type_, ir.UnknownType):
                            expr = propagate_types(match_expr_type(node.scope.body[-1], ir.VoidType(None)))
                        else:
                            expr = propagate_types(node.scope.body[-1])

                        node.scope.body[-1] = expr if isinstance(expr.type_, ir.VoidType) else ir.Drop(expr)
                    else:
                        node.scope.body[-1] = propagate_types(node.scope.body[-1])
                else:
                    match node.scope.body[-1]:
                        case ir.Expr():
                            node.scope.body[-1] = propagate_types(match_expr_type(node.scope.body[-1], node.type_))
                        case ir.FunctionReturn():
                            node.scope.body[-1] = propagate_types(node.scope.body[-1])
                        case _:
                            # TODO: check if statements always return
                            node.scope.body[-1] = propagate_types(node.scope.body[-1])
                            # raise Exception(f"Unexpected node type in function body: {type(node.scope.body[-1])}")

        case ir.Scope():
            # TODO: while/if/else expressions
            for i in range(len(node.body)):
                if isinstance(node.body[i], ir.Asm):
                    node.body[i] = propagate_types(match_expr_type(node.body[i], ir.VoidType(None)))
                elif isinstance(node.body[i], ir.Expr):
                    expr = propagate_types(node.body[i])
                    assert not isinstance(expr.type_, ir.UnknownType)
                    node.body[i] = expr if isinstance(expr.type_, ir.VoidType) else ir.Drop(expr)
                else:
                    node.body[i] = propagate_types(node.body[i])

            node.attrs = traverse_ir.traverse_dict(propagate_types, node.attrs)

        case ir.Assignment():
            assert isinstance(node.lvalue, ir.VarRef)
            node.expr = propagate_types(match_expr_type(node.expr, node.lvalue.type_))
            assert isinstance(node.expr, ir.Expr)
            match node.lvalue:
                case ir.VarRef():
                    assert node.lvalue.type_ == node.expr.type_
                case ir.ArgRef():
                    raise ValueError("Setting argument not allowed")
                case _:
                    raise NotImplementedError(type(node.lvalue))

        case ir.SetLocal():
            node.expr = propagate_types(match_expr_type(node.expr, node.var.type_))

        case ir.SetItem():
            node.expr = propagate_types(node.expr)
            node.idx = propagate_types(match_expr_type(node.idx, node.idx_type))
            node.value = propagate_types(match_expr_type(node.value, node.expr.type_.primitive().element_type))

        case ir.GetItem():
            node.type_ = node.expr.type_.primitive().element_type
            node.expr = propagate_types(node.expr)
            node.idx = propagate_types(match_expr_type(node.idx, node.idx_type))

        case ir.Cast():
            assert isinstance(node.type_, ir.TypeRef)
            assert isinstance(node.type_.type_, ir.TypeDef)
            cast_from = node.type_.type_.scope.lookup("__cast_from")
            expr = propagate_types(node.expr)
            # TODO: overloaded
            assert isinstance(cast_from, ir.MacroDef)
            assert len(cast_from.func.type_.args) == 1
            cast_type = cast_from.func.type_.args[0].type_
            assert cast_type == expr.type_
            return ir.MacroInst(node.info, node.type_, ir.MacroRef(None, cast_from), [expr])

        case ir.Match():
            assert isinstance(node.match_expr.expr, ir.Expr)
            node.match_expr.var.type_ = node.match_expr.expr.type_

            node.match_expr = propagate_types(node.match_expr)
            for i, case in enumerate(node.cases):
                match case:
                    case ir.MatchCaseEnum():
                        assert isinstance(case.enum, ir.TypeRef)
                        assert isinstance(case.enum.type_, ir.EnumValueType)
                        assert len(case.args) == len(case.enum.type_.fields.field_types[1:])
                        case.args = [
                            propagate_types(match_expr_type(arg, type_))
                            for arg, type_ in zip(case.args, case.enum.type_.fields.field_types[1:])
                        ]
                        case.scope = propagate_types(case.scope)

                    case ir.MatchCase():
                        assert isinstance(node.match_expr.expr, ir.Expr)
                        case.expr = propagate_types(match_expr_type(case.expr, node.match_expr.expr.type_))
                        case.scope = propagate_types(case.scope)

                    case _:
                        raise NotImplementedError(case)

        case _:
            return traverse_ir.traverse(propagate_types, node)

    return node


def match_expr_type(expr: ir.Node, type_: ir.Type):
    match expr:
        case ir.TypeRef():
            match expr.primitive():
                case ir.EnumValueType() as enum if len(enum.fields.field_types) == 1:
                    expr = ir.TupleInst(expr.info, expr, [ir.IntLiteral(None, enum.discr)])
                case _:
                    raise NotImplementedError(expr)

        case ir.ReinterpretCast():
            assert isinstance(expr.type_, ir.UnknownType)
            assert not isinstance(type_, ir.UnknownType)
            expr.type_ = type_
            return expr

    assert isinstance(expr, ir.Expr)
    match expr.type_:
        case ir.UnknownType():
            assert isinstance(type_, (ir.TypeRef, ir.UnknownType, ir.VoidType))
            expr.type_ = type_

        case ir.AstType(name="__int"):
            match type_.primitive():
                case ir.TypeDef() as type_primitive:
                    # TODO: __from_literal overloading
                    from_literal = type_primitive.scope.lookup("__from_literal")
                    assert isinstance(from_literal, ir.MacroDef)
                    assert len(from_literal.func.type_.args) == 1
                    source_type = from_literal.func.type_.args[0].type_.primitive()
                    assert source_type == expr.type_, source_type
                    assert isinstance(type_, ir.TypeRef)
                    return ir.MacroInst(expr.info, type_, ir.MacroRef(None, from_literal), [expr])
                case ir.AstType(name="__int"):
                    return expr
                case other:
                    raise NotImplementedError(type(other))

        case ir.AstType(name="__string_literal"):
            assert isinstance(type_.primitive(), ir.ArrayType)
            assert isinstance(expr, ir.StringLiteral)
            assert isinstance(expr.temp_var.type_, ir.UnknownType)
            assert isinstance(expr.temp_var.type_, ir.UnknownType)
            assert isinstance(type_, ir.TypeRef)
            expr.temp_var.type_ = expr.temp_var.type_ = type_

        case ir.TypeRef(type_=ir.TypeDef() as expr_type):
            if not expr_type.has_base_class(type_):
                raise Exception(f"{expr.type_} is not compatible with {type_}")

        case _:
            if expr.type_ != type_:
                raise Exception(f"Type mismatch: {expr.type_} vs {type_}")

    return expr


def specialize_match(node: ir.Node) -> ir.Node:
    match node:
        case ir.Match():
            assert isinstance(node.match_expr.expr, ir.Expr)
            assert node.match_expr.var.type_ == node.match_expr.expr.type_
            if isinstance(node.match_expr.expr.type_.primitive(), ir.EnumType):
                cases = [ir.MatchCaseEnum.from_case(case) for case in node.cases]
                return ir.MatchEnum(node.info, node.match_expr, cases, node.scope)
            else:
                raise NotImplementedError

        case _:
            return traverse_ir.traverse(specialize_match, node)
    return node


def check_no_unknown_types(node: ir.Node) -> ir.Node:
    match node:
        case ir.UnknownType():
            raise Exception(f"Unknown type: {node}")

        case ir.TemplateDef():
            # Only check instances, not template
            node.instances = traverse_ir.traverse_dict(check_no_unknown_types, node.instances)
            return node

        case _:
            return traverse_ir.traverse(check_no_unknown_types, node)
    return node


def inline_macros(node: ir.Node, scope=None) -> ir.Node:
    match node:
        case ir.FunctionDef():
            return traverse_ir.traverse(inline_macros, node, node.scope)
        case ir.MacroInst():
            return traverse_ir.inline(node.macro, scope, [inline_macros(arg, scope) for arg in node.args])
            # return inline_macros(traverse_ir.inline(node.macro, scope, node.args), scope)  # slow
        case _:
            return traverse_ir.traverse(inline_macros, node, scope)


def done(node: ir.Node) -> ir.Node:
    return node


toplevel_ast_passes: list = [
    register_toplevel_decls,
    register_toplevel_methods,
    check_unallowed_toplevel_decls,
]


ir_passes: list = [
    translate_toplevel_type_decls,
    check_no_untranslated_types,
    translate_function_defs,
    check_no_untranslated_nodes,
    resolve_member_access,
    instantiate_templates,
    resolve_member_access,
    write_tree("inner.ir"),
    propagate_types,
    specialize_match,
    check_no_unknown_types,
    inline_macros,
    done,
]


def run(prog: ast.Module):
    root_scope = ir.Scope(None, "root")
    root_scope.register_type("__int", ir.AstType(None, "__int"))

    module = ir.Module(prog.info, ir.Scope(root_scope, "module"))
    for pass_ in toplevel_ast_passes:
        print("Pass:", pass_.__name__)
        pass_(prog, module)

    # import pprint
    # pprint.pp(module)

    for pass_ in ir_passes:
        print("Pass:", pass_.__name__)
        module = pass_(module)

    return module
