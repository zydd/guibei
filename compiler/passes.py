from compiler import ast
from compiler import ir
from compiler import traverse_ast
from compiler import traverse_ir
from compiler import eval_wasm


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
            enum_scope = ir.Scope(module.scope, node.name)
            discr_type = module.scope.attrs["__enum_discr"]
            assert isinstance(discr_type, ir.TypeDef)
            discr_type = ir.TypeRef(None, discr_type)

            if all(value.fields is None for value in node.values):
                enum_type: ir.Type = ir.EnumIntType(node.info, discr_type, node.name, enum_scope)
                for i, val in enumerate(node.values):
                    enum_scope.add_method(val.name, ir.EnumInt(val.info, ir.TypeRef(None, enum_type), i))
            else:
                enum_type = ir.EnumType(node.info, node.name, enum_scope, len(node.values), discr_type)
                for i, val in enumerate(node.values):
                    enum_scope.register_type(val.name, ir.EnumValueType.translate(enum_type, i, discr_type, val))

            module.scope.register_type(node.name, enum_type)

        case ast.TemplateDef():
            module.scope.register_type(node.name, ir.TemplateDef.translate(node, module.scope))

        case ast.FunctionDef():
            fn_def = ir.FunctionDef.translate(node, module.scope)
            module.scope.add_method(node.name, fn_def)

        case ast.MacroDef():
            module.scope.add_method(node.name, ir.MacroDef.translate(node, module.scope))

        case ast.AstMacroDef():
            module.scope.add_method(node.name, ir.AstMacroDef.translate(node, module.scope))

        case ast.Asm():
            module.add_asm(ir.Untranslated(node))

        case ast.ConstDecl():
            module.scope.add_method(node.name, ir.ConstDecl.translate(node, module.scope))

        case _:
            return node


def _register_impl_methods(module: ir.Module, type_: ir.TypeDef, method: ast.Node):
    match method:
        case ast.FunctionDef():
            tr_method = ir.FunctionDef.translate(method, type_.scope)
            if method.name.startswith("("):
                module.scope.add_method(method.name, ir.FunctionRef(None, tr_method), overload=True)
            type_.scope.add_method(method.name, tr_method)

        case ast.MacroDef():
            macro = ir.MacroDef.translate(method, type_.scope)
            if method.name.startswith("("):
                module.scope.add_method(method.name, ir.MacroRef(method.name, macro), overload=True)
                type_.scope.add_method(method.name, macro)
            elif method.name == "__from_literal":
                # TODO: match types, stop storing macro twice
                type_.scope.add_method(method.name, ir.MacroRef(None, macro), overload=True)

                # Shadowed macro def
                type_.scope.add_method(type_.scope.new_child_name(method.name), macro)
            else:
                type_.scope.add_method(method.name, macro)

        case ast.AstMacroInst():
            macro = module.scope.lookup(method.name)
            assert isinstance(macro, ir.AstMacroDef)
            arg_names = [arg.name for arg in macro.func.type_.args]
            arg_map: dict = dict(zip(arg_names, method.arg.field_values))
            ast_nodes = [n.ast_node for n in macro.func.scope.body]  # type:ignore[attr-defined]  # Untranslated
            inlined = traverse_ast.inline(ast_nodes, arg_map)
            for m in inlined:
                _register_impl_methods(module, type_, m)

        case _:
            raise NotImplementedError(type(method))


def register_toplevel_methods(node: ast.Node, module: ir.Module):
    match node:
        case ast.Module():
            traverse_ast.traverse(register_toplevel_methods, node, module)

        case ast.TypeImpl():
            assert isinstance(node.type_, ast.TypeIdentifier)
            type_ = module.scope.lookup_type(node.type_.name)
            assert isinstance(type_, ir.TypeDef)
            for method in node.methods:
                _register_impl_methods(module, type_, method)

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


def check_disallowed_toplevel_decls(node: ast.Node, module: ir.Module):
    assert isinstance(node, ast.Module)
    assert len(node.stmts) == 0, f"{type(node.stmts[0]).__name__} not allowed as a top level declaration"


def translate_toplevel_type_decls(node: ir.Node, scope=None) -> ir.Node:
    match node:
        case ir.Module():
            node.scope.attrs = traverse_ir.traverse_dict(translate_toplevel_type_decls, node.scope.attrs, node.scope)

        case ir.UntranslatedType(ast_node=ast.NativeArrayType() as ast_node):
            tr_type = translate_toplevel_type_decls(ir.UntranslatedType(ast_node.element_type), scope)
            assert isinstance(tr_type, ir.Type)
            return ir.NativeArrayType(ast_node.info, tr_type)

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
                case ir.SelfType() | ir.BuiltinType() | ir.TypeRef() | ir.TemplateArgRef():
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

        case ir.UntranslatedType(ast_node=ast.ArrayType() as ast_node):
            array = ir.TemplateRef(ast_node.info, scope.root.attrs["__array"])
            elem_type = translate_toplevel_type_decls(ir.UntranslatedType(ast_node.element_type), scope)
            assert isinstance(elem_type, ir.Type)
            return ir.TemplateInst(ast_node.info, array, [elem_type])

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

        case ir.AstMacroDef():
            return node

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

            if node.type_.args and node.type_.args[0].name == "self":
                self_type = scope.lookup("Self")
                if isinstance(node.type_.args[0].type_, ir.UnknownType):
                    node.type_.args[0].type_ = self_type
                else:
                    assert node.type_.args[0].type_ == self_type, "Self type mismatch"

            return node

        case ir.Untranslated(ast_node=ast.VarDecl() as var):
            var_type = translate_toplevel_type_decls(
                ir.UntranslatedType(var.type_) if var.type_ else ir.UnknownType(), scope
            )
            assert isinstance(var_type, ir.Type)
            var_decl = ir.VarDecl(var.info, var.name, var_type)
            scope.register_local(var_decl.name, var_decl)
            if var.init:
                var_init = ir.SetLocal(var.init.info, ir.VarRef(None, var_decl), ir.Untranslated(var.init))
                return translate_function_defs(var_init, scope)
            else:
                return ir.VoidExpr(var.info)

        case ir.Untranslated(ast_node=ast.Identifier() | ast.TypeIdentifier() as id):
            attr = scope.lookup(id.name)
            if isinstance(id, ast.TypeIdentifier):
                assert isinstance(attr, ir.Type)

            match attr:
                case (
                    ir.VarRef()
                    | ir.ArgRef()
                    | ir.TypeRef()
                    | ir.SelfType()
                    | ir.TemplateArgRef()
                    | ir.Builtin()
                    | ir.EnumInt()
                ):
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
                case ir.ConstDecl():
                    return ir.ConstRef(id, attr)
                case _:
                    raise NotImplementedError(type(attr))

        case ir.Untranslated(ast_node=ast.TupleExpr() as ast_node):
            if len(ast_node.field_values) == 1:
                return translate_function_defs(ir.Untranslated(ast_node.field_values[0]), scope)
            else:
                fields: list = [
                    translate_function_defs(ir.Untranslated(field), scope) for field in ast_node.field_values
                ]
                if not fields:
                    return ir.VoidExpr(ast_node.info)
                else:
                    assert all(isinstance(field, ir.Expr) for field in fields)
                    return ir.TupleExpr(ast_node.info, ir.UnknownType(), fields)

        case ir.Untranslated(ast_node=ast.While() as while_stmt):
            pre_condition = ir.Untranslated(while_stmt.condition)
            loop_scope = ir.Scope(scope, "__while", body=[ir.Untranslated(stmt) for stmt in while_stmt.body])
            loop_scope.break_scope = loop_scope.name + ".__block"  # FIXME: declare properly
            loop = ir.Loop(while_stmt.info, pre_condition, loop_scope)
            return translate_function_defs(loop, loop_scope)

        case ir.Untranslated(ast_node=ast.Break() as break_stmt):
            return ir.Break(break_stmt.info, scope.break_scope, ir.VoidExpr(None))

        case ir.Untranslated(ast_node=ast.GetItem() as ast_node):
            expr = translate_function_defs(ir.Untranslated(ast_node.expr), scope)
            idx = translate_function_defs(ir.Untranslated(ast_node.idx), scope)
            match expr:
                case ir.Expr():
                    assert isinstance(idx, ir.Expr)
                    return ir.GetItem(node.info, ir.UnknownType(), expr, idx)

                case ir.TemplateRef():
                    assert isinstance(idx, ir.Type)
                    return ir.TemplateInst(node.info, expr, [idx])

                case _:
                    raise NotImplementedError(type(expr))

        case ir.Untranslated(ast_node=ast.BinOp() as ast_node):
            func = scope.module_scope.lookup(f"({ast_node.op})")
            assert isinstance(func, (ir.FunctionDef, ir.MacroDef, ir.OverloadedFunction, ir.FunctionRef, ir.MacroRef))
            func = func.ref()
            lhs = translate_function_defs(ir.Untranslated(ast_node.lhs), scope)
            rhs = translate_function_defs(ir.Untranslated(ast_node.rhs), scope)
            assert isinstance(lhs, ir.Expr)
            assert isinstance(rhs, ir.Expr)
            return ir.Call(ast_node.info, func, ir.TupleExpr(None, ir.UnknownType(), [lhs, rhs]))

        case ir.Untranslated(ast_node=ast.UnaryL(op="-", arg=ast.IntLiteral() as value)):
            return ir.IntLiteral(value, -value.value)

        case ir.Untranslated(ast_node=ast.UnaryL() | ast.UnaryR() as ast_node):
            func = scope.lookup(f"({ast_node.op})")
            assert isinstance(func, (ir.FunctionDef, ir.MacroDef, ir.OverloadedFunction))
            func = func.ref()
            tr_arg = translate_function_defs(ir.Untranslated(ast_node.arg), scope)
            assert isinstance(tr_arg, ir.Expr)
            return ir.Call(ast_node, func, ir.TupleExpr(None, ir.UnknownType(), [tr_arg]))

        case ir.Untranslated(ast_node=ast.Call(callee=ast.Identifier("__reinterpret_cast"), arg=arg)):
            return ir.ReinterpretCast(
                node.info,
                ir.UnknownType(),
                translate_function_defs(ir.Untranslated(arg), scope),  # type:ignore[arg-type]
            )

        case ir.Untranslated(ast_node=ast.Assignment(lvalue=ast.GetItem() as getter) as assign):
            lvalue = translate_function_defs(ir.Untranslated(getter.expr), scope)
            idx = translate_function_defs(ir.Untranslated(getter.idx), scope)
            assign_value = translate_function_defs(ir.Untranslated(assign.expr), scope)
            assert isinstance(lvalue, ir.Expr)
            assert isinstance(idx, ir.Expr)
            assert isinstance(assign_value, ir.Expr)
            return ir.SetItem(assign.info, lvalue, idx, assign_value)

        case ir.Scope():
            node.attrs = traverse_ir.traverse_dict(translate_function_defs, node.attrs, node)
            node.body = traverse_ir.traverse_list(translate_function_defs, node.body, node)
            return node

        case ir.MatchCaseEnum():
            node.enum = translate_function_defs(node.enum, scope)
            node.args = traverse_ir.traverse_list(_translate_match_pattern, node.args, node.scope)
            node.scope = translate_function_defs(node.scope, scope)  # type:ignore[assignment]
            return node

        case ir.Untranslated():
            return translate_function_defs(node.translate(scope), scope)

        case ir.AstMacroDef():
            return node

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
            raise NotImplementedError(type(node))


def _expand_call_args(arg: ir.Node) -> list:
    match arg:
        case ir.TupleExpr():
            return arg.args

        case ir.VoidExpr():
            return []

        case _:
            return [arg]


def resolve_member_access(node: ir.Node, scope=None) -> ir.Node:
    node = traverse_ir.traverse_scoped(resolve_member_access, node, scope)

    match node:
        case ir.GetAttr():
            try:
                idx = int(node.attr)
            except ValueError:
                idx = None

            if idx is not None:
                assert isinstance(node.expr, ir.Expr)

                if isinstance(node.expr.type_, ir.UnknownType):
                    return node

                assert isinstance(node.expr.type_, ir.TypeRef)
                match node.expr.type_.primitive():
                    case ir.EnumValueType() as enum:
                        return ir.GetTupleItem(node.info, enum.field_types[idx], node.expr, idx + 1)

                    case ir.TupleType() as tuple_:
                        field_type = tuple_.field_types[idx]
                        assert isinstance(field_type, ir.TypeRef), field_type
                        return ir.GetTupleItem(node.info, field_type, node.expr, idx)

                    case primitive:
                        raise NotImplementedError(type(primitive))

            match node.expr:
                case ir.TemplateArgRef():
                    # FIXME: translate/annotate templated methods
                    return node

                case ir.TypeRef():
                    match node.expr.type_:
                        case ir.TypeDef():
                            if node.attr == "__type_reference":
                                return node.expr.type_.get_type_reference()
                            elif node.attr == "__default":
                                match node.expr.type_.primitive():
                                    case ir.IntegralType() as integral:
                                        return ir.Asm(
                                            node.info,
                                            ir.WasmExpr(node.info, [f"{integral.native_type}.const 0"]),
                                            node.expr,
                                        )
                                    case ir.TupleType() | ir.NativeArrayType() | ir.EnumType():
                                        return ir.Asm(
                                            node.info,
                                            ir.WasmExpr(node.info, [["ref.null", f"${node.expr.name}"]]),
                                            node.expr,
                                        )
                                    case other:
                                        raise NotImplementedError(type(other))

                            try:
                                attr = node.expr.type_.get_attr(node.attr)
                            except KeyError as e:
                                raise KeyError(
                                    f"Type '{node.expr.type_.name}' has no member '{node.attr}'",
                                ) from e

                            match attr:
                                case ir.TypeRef() | ir.AsmType() | ir.EnumInt():
                                    return attr
                                case ir.FunctionDef():
                                    if (
                                        isinstance(node.expr.primitive(), ir.EnumValueType)
                                        and attr.type_.args[0].name == "self"
                                    ):
                                        return ir.BoundMethod(
                                            node.info,
                                            ir.UnknownType(),
                                            ir.FunctionRef(None, attr),
                                            ir.EnumInst(node.expr.info, node.expr, node.expr.primitive().discr, []),
                                        )
                                    else:
                                        return ir.FunctionRef(node.info, attr)
                                case ir.EnumValueType():
                                    return ir.TypeRef(None, attr)
                                case ir.MacroDef():
                                    return ir.MacroRef(None, attr)
                                case ir.ConstDecl():
                                    return ir.ConstRef(None, attr)
                                case _:
                                    raise NotImplementedError(type(attr))
                        case _:
                            raise NotImplementedError(type(node.expr.type_))

                case ir.StringLiteral():
                    match node.attr:
                        case "__len":
                            return ir.IntLiteral(node.info, len(node.expr.value))
                        case "__int_le":
                            return ir.IntLiteral(node.info, int.from_bytes(node.expr.value.encode(), "little"))
                        case _:
                            raise NotImplementedError(node.attr)

                case ir.Expr():
                    match node.expr.type_:
                        case ir.TypeRef():
                            obj_type_prim = node.expr.type_.primitive()
                            if isinstance(obj_type_prim, ir.NamedTupleType) and node.attr in obj_type_prim.field_names:
                                field = obj_type_prim.field_names.index(node.attr)
                                return ir.GetTupleItem(node.info, obj_type_prim.field_types[field], node.expr, field)
                            elif isinstance(node.expr.type_.type_, ir.TypeDef):
                                method = node.expr.type_.get_attr(node.attr)
                                assert isinstance(method, ir.FunctionDef)
                                if method.type_.args[0].name == "self":
                                    return ir.BoundMethod(
                                        node.info, ir.UnknownType(), ir.FunctionRef(None, method), node.expr
                                    )
                                else:
                                    raise RuntimeError("Calling static method from object")
                                    # return method
                            else:
                                raise NotImplementedError

                        case ir.BuiltinType(name="__str"):
                            match node.attr:
                                case "__len" | "__int_le":
                                    node.type_ = ir.BuiltinType("__int")
                                case _:
                                    raise NotImplementedError

                        case _:
                            return node

                case ir.SelfType() | ir.TemplateInst():
                    return node

                case _:
                    # TODO
                    breakpoint()
                    return node
                    raise NotImplementedError(type(node.obj))

        case ir.GetItem():
            match node.expr.type_.primitive():
                case ir.NativeArrayType() as array_primitive:
                    return ir.GetNativeArrayItem(node.info, array_primitive.element_type, node.expr, node.idx)

                case ir.TemplateInst() | ir.UnknownType() | ir.SelfType():
                    return node

                case _:
                    assert isinstance(node.expr.type_, ir.TypeRef)
                    assert isinstance(node.expr.type_.type_, ir.TypeDef)
                    if "[]" in node.expr.type_.type_.scope.attrs:
                        method = node.expr.type_.type_.scope.attrs["[]"]
                        if isinstance(method, ir.OverloadedFunction):
                            breakpoint()
                        assert isinstance(method, (ir.FunctionDef, ir.MacroDef))
                        method = ir.BoundMethod(node.info, ir.UnknownType(), method.ref(), node.expr)
                        call = ir.Call(node.info, method, node.idx)
                        return resolve_member_access(call, scope)

        case ir.SetItem():
            match node.lvalue.type_.primitive():
                case ir.NativeArrayType():
                    return ir.SetNativeArrayItem(node.info, node.lvalue, node.idx, node.value)

                case ir.TemplateInst() | ir.UnknownType():
                    return node

                case _:
                    assert isinstance(node.lvalue.type_, ir.TypeRef)
                    assert isinstance(node.lvalue.type_.type_, ir.TypeDef)
                    if "[]=" in node.lvalue.type_.type_.scope.attrs:
                        method = node.lvalue.type_.type_.scope.attrs["[]="]
                        if isinstance(method, ir.OverloadedFunction):
                            breakpoint()
                        assert isinstance(method, (ir.FunctionDef, ir.MacroDef))
                        method = ir.BoundMethod(node.info, ir.UnknownType(), method.ref(), node.lvalue)
                        call = ir.Call(node.info, method, ir.TupleExpr(None, ir.UnknownType(), [node.idx, node.value]))
                        return resolve_member_access(call, scope)
                    pass

        case ir.Assignment():
            assert isinstance(node.expr, ir.Expr)
            match node.lvalue:

                case ir.VarRef() | ir.ArgRef():
                    return ir.SetLocal(node.info, node.lvalue, node.expr)

                case ir.GetAttr():
                    return node

                case ir.GetTupleItem():
                    return ir.SetTupleItem(node.info, node.lvalue.expr, node.lvalue.idx, node.expr)

                case _:
                    raise NotImplementedError(type(node.lvalue))

        case ir.Call():
            match node.callee:
                case ir.FunctionRef():
                    return ir.FunctionCall(
                        node.info,
                        node.callee.func.type_.ret_type,
                        node.callee,
                        _expand_call_args(node.arg),
                    )

                case ir.BoundMethod():
                    return ir.FunctionCall(
                        node.info,
                        node.callee.func.func.type_.ret_type,
                        node.callee.func,
                        [node.callee.obj] + _expand_call_args(node.arg),
                    )

                case ir.TypeRef():
                    match node.callee.primitive():
                        case ir.EnumValueType() as enum_val:
                            args: list = _expand_call_args(node.arg)
                            assert all(isinstance(arg, ir.Expr) for arg in args)
                            return ir.EnumInst(node.info, node.callee, enum_val.discr, args)

                        case ir.TupleType():
                            match node.arg:
                                case ir.TupleExpr():
                                    return ir.TupleInst(node.info, node.callee, node.arg.args)
                                case _:
                                    assert isinstance(node.arg, ir.Expr)
                                    return ir.Cast(node.info, node.callee, node.arg)

                        case ir.TypeDef() | ir.IntegralType():
                            args = _expand_call_args(node.arg)
                            assert len(args) == 1
                            assert isinstance(args[0], ir.Expr)
                            return ir.Cast(node.info, node.callee, args[0])

                        case _:
                            raise NotImplementedError(node.callee)

                case ir.MacroRef():
                    return ir.MacroInst(
                        node.info, node.callee.macro.func.type_.ret_type, node.callee, _expand_call_args(node.arg)
                    )

                case ir.GetAttr() | ir.SelfType() | ir.TemplateInst():
                    return node

                case ir.OverloadedFunction():
                    assert isinstance(node.arg, ir.TupleExpr)
                    call_args: list = node.arg.args
                    arg_types = [arg.type_ for arg in call_args]
                    matches: list[ir.FunctionRef | ir.MacroRef] = []
                    for method in node.callee.overloads:
                        assert isinstance(method, ir.FunctionRef)
                        method_arg_types = [arg.type_ for arg in method.func.type_.args]
                        comp = [t1.has_base_class(t2) for t1, t2 in zip(arg_types, method_arg_types)]

                        if all(comp):
                            return ir.FunctionCall(node.info, method.func.type_.ret_type, method, call_args)

                        if any(comp):
                            matches.append(method)

                    if not matches:
                        if any(isinstance(arg_type, ir.UnknownType) for arg_type in arg_types):
                            # Possibly before template substitution
                            return node

                        raise TypeError(
                            f"No matching overload for function '{node.callee.name}' with argument types {arg_types}"
                        )

                    elif len(matches) == 1:
                        method = matches[0]
                        assert isinstance(method, ir.FunctionRef)
                        return ir.FunctionCall(node.info, method.func.type_.ret_type, method, call_args)

                    else:
                        overloads = ir.OverloadedFunction(node.info, node.callee.name, matches)
                        return ir.Call(node.info, overloads, node.arg, node.type_)

                case ir.Builtin(name="__enumerate"):
                    node.type_ = ir.BuiltinType("__iter")

                case _:
                    raise NotImplementedError(type(node.callee))

        case ir.AstMacroDef():
            return node

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

    return node


def check_no_untranslated_nodes(node: ir.Node) -> ir.Node:
    match node:
        case ir.Untranslated():
            raise Exception(f"Untranslated node: {node}")
        case ir.AstMacroDef():
            return node
        case _:
            return traverse_ir.traverse(check_no_untranslated_nodes, node)
    return node


def propagate_types(node: ir.Node):
    match node:
        case ir.Module():
            node.scope = propagate_types(node.scope)
            node.asm = [propagate_types(match_expr_type(asm, ir.VoidType(None))) for asm in node.asm]

        case ir.TemplateDef():
            # Only type-check instances
            node.instances = traverse_ir.traverse_dict(propagate_types, node.instances)
            return node

        case ir.TemplateFor():
            match node.iterable:
                case ir.Call(callee=ir.Builtin(name="__enumerate"), arg=iterable):
                    assert len(node.bindings) == 2
                    if not isinstance(node.bindings[0].type_, ir.BuiltinType):
                        assert isinstance(node.bindings[0].type_, ir.UnknownType)
                        assert isinstance(node.bindings[1].type_, ir.UnknownType)
                        node.bindings[0].type_ = ir.BuiltinType("__int")

                        # TODO: generalize
                        assert isinstance(iterable, ir.Expr)
                        assert iterable.type_ == ir.BuiltinType("__str")
                        # __str == __array[__int]
                        node.bindings[1].type_ = ir.BuiltinType("__int")

                    node.body = propagate_types(node.body)
                    return node
                case _:
                    raise NotImplementedError

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

        case ir.EnumInst():
            assert isinstance(node.type_, ir.TypeRef)
            primitive = node.type_.primitive()
            assert isinstance(primitive, ir.EnumValueType)
            assert len(node.args) == len(primitive.field_types)
            node.args = [
                propagate_types(match_expr_type(arg, field_type))
                for arg, field_type in zip(node.args, primitive.field_types)
            ]

        case ir.TupleInst():
            assert isinstance(node.type_, ir.TypeRef), node.type_
            primitive = node.type_.primitive()
            assert isinstance(primitive, ir.TupleType)
            assert len(node.args) == len(primitive.field_types)
            node.args = [
                propagate_types(match_expr_type(arg, field_type))
                for arg, field_type in zip(node.args, primitive.field_types)
            ]

        case ir.FunctionDef():
            for i in range(len(node.scope.body) - 1):
                if isinstance(node.scope.body[i], ir.Asm):
                    node.scope.body[i] = propagate_types(match_expr_type(node.scope.body[i], ir.VoidType(None)))
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
                            assert isinstance(node.type_.ret_type, ir.VoidType), node.name
                            # TODO: check if statements always return
                            node.scope.body[-1] = propagate_types(node.scope.body[-1])
                            # raise Exception(f"Unexpected node type in function body: {type(node.scope.body[-1])}")

        case ir.Block():
            for i in range(len(node.scope.body) - 1):
                if isinstance(node.scope.body[i], ir.Asm):
                    node.scope.body[i] = propagate_types(match_expr_type(node.scope.body[i], ir.VoidType(None)))
                else:
                    node.scope.body[i] = propagate_types(node.scope.body[i])

            assert not node.scope.attrs
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
            node.attrs = traverse_ir.traverse_dict(propagate_types, node.attrs)
            for i in range(len(node.body)):
                if isinstance(node.body[i], ir.Asm):
                    node.body[i] = propagate_types(match_expr_type(node.body[i], ir.VoidType(None)))
                else:
                    node.body[i] = propagate_types(node.body[i])

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

        case ir.SetNativeArrayItem():
            assert isinstance(node.lvalue.type_, ir.TypeRef)
            assert isinstance(node.lvalue.type_.type_, ir.TypeDef)
            method = node.lvalue.type_.type_.scope.attrs["[]="]
            assert isinstance(method, (ir.FunctionDef, ir.MacroDef))
            idx_type = method.type_.args[1].type_

            node.lvalue = propagate_types(node.lvalue)
            node.idx = propagate_types(match_expr_type(node.idx, idx_type))
            node.value = propagate_types(match_expr_type(node.value, node.lvalue.type_.primitive().element_type))

        case ir.GetNativeArrayItem():
            assert isinstance(node.expr.type_, ir.TypeRef)
            assert isinstance(node.expr.type_.type_, ir.TypeDef)
            method = node.expr.type_.type_.scope.attrs["[]"]
            assert isinstance(method, (ir.FunctionDef, ir.MacroDef))
            idx_type = method.type_.args[1].type_

            node.expr = propagate_types(node.expr)
            node.idx = propagate_types(match_expr_type(node.idx, idx_type))

        case ir.Cast():
            assert isinstance(node.type_, ir.TypeRef)
            assert isinstance(node.type_.type_, ir.TypeDef)
            expr = propagate_types(node.expr)
            return explicit_cast(expr, node.type_)

        case ir.Match():
            assert isinstance(node.match_expr.expr, ir.Expr)
            node.match_expr.var.type_ = node.match_expr.expr.type_

            node.match_expr = propagate_types(node.match_expr)
            for i, case in enumerate(node.cases):
                match case:
                    case ir.MatchCaseEnum():
                        assert isinstance(case.enum, ir.TypeRef)
                        assert isinstance(case.enum.type_, ir.EnumValueType)
                        assert len(case.args) == len(case.enum.type_.field_types)
                        case.args = [
                            propagate_types(match_expr_type(arg, type_))
                            for arg, type_ in zip(case.args, case.enum.type_.field_types)
                        ]
                        case.scope = propagate_types(case.scope)

                    case ir.MatchIntCase():
                        case.scope = propagate_types(case.scope)

                    case ir.MatchCase():
                        assert isinstance(node.match_expr.expr, ir.Expr)
                        case.expr = propagate_types(match_expr_type(case.expr, node.match_expr.expr.type_))
                        case.scope = propagate_types(case.scope)

                    case _:
                        raise NotImplementedError(case)

        case ir.AstMacroDef():
            return node

        case _:
            return traverse_ir.traverse(propagate_types, node)

    return node


def drop_unused_result(node: ir.Node) -> ir.Node:
    match node:
        case ir.TemplateDef():
            # Only type-check instances
            node.instances = traverse_ir.traverse_dict(propagate_types, node.instances)
            return node

        case ir.Scope():
            # TODO: while/if/else expressions
            for i in range(len(node.body) - 1):
                expr = node.body[i]
                if isinstance(expr, ir.Expr):
                    assert not isinstance(expr.type_, ir.UnknownType)
                    if not isinstance(expr.type_, ir.VoidType):
                        node.body[i] = ir.Drop(expr)

    return traverse_ir.traverse(drop_unused_result, node)


def convert_enum_inst(node: ir.Node) -> ir.Node:
    node = traverse_ir.traverse(convert_enum_inst, node)

    match node:
        # case ir.GetEnumItem():
        #     return ir.GetTupleItem(node.info, node.type_, node.expr, node.idx + 1)

        case ir.EnumInst():
            enum_value_type = node.type_.primitive()
            assert isinstance(enum_value_type, ir.EnumValueType)
            return ir.TupleInst(
                node.info,
                node.type_,
                [match_expr_type(ir.IntLiteral(None, node.discr), enum_value_type.discr_type)] + node.args,
            )

        case ir.EnumInt():
            assert isinstance(node.type_, ir.TypeRef)
            assert isinstance(node.type_.type_, ir.EnumIntType)
            assert node.type_.type_.super_
            return match_expr_type(ir.IntLiteral(None, node.discr), node.type_.type_.super_)

    return node


def _check_match_expr_type_result(func):
    def wrapper(expr: ir.Node, type_: ir.Type):
        res = func(expr, type_)
        assert isinstance(res, ir.Expr), f"Expected Expr, got {type(res)}"
        assert (
            res.type_ == type_
            or isinstance(res.type_, ir.TypeRef)
            and isinstance(res.type_.type_, ir.TypeDef)
            and res.type_.has_base_class(type_)
        ), f"Type mismatch: expected {type_}, got {res.type_}"
        return res

    return wrapper


def implicit_cast_literal(expr: ir.Expr, type_: ir.Type):
    assert isinstance(expr.type_, ir.BuiltinType)
    match type_:
        case ir.TypeRef():
            # TODO: __from_literal overloading
            assert isinstance(type_.type_, ir.TypeDef)
            cast_type = type_.type_
            try:
                from_literal = cast_type.scope.attrs["__from_literal"]
            except KeyError:
                raise RuntimeError(f"Implicit conversion from {expr.type_} to {type_} not allowed")

            if isinstance(from_literal, ir.OverloadedFunction):
                (from_literal,) = list(
                    filter(
                        lambda x: x.macro.func.type_.args[0].type_ == expr.type_, from_literal.overloads  # type:ignore
                    )
                )

            assert isinstance(from_literal, ir.MacroRef)
            assert len(from_literal.macro.func.type_.args) == 1
            source_type = from_literal.macro.func.type_.args[0].type_.primitive()
            assert source_type == expr.type_, source_type
            assert isinstance(type_, ir.TypeRef)
            return ir.ImplicitCast(expr.info, type_, from_literal, expr)

        case ir.BuiltinType() if expr.type_.name == type_.name:
            return expr

        case other:
            raise NotImplementedError(type(other))


def explicit_cast(expr: ir.Expr, type_: ir.Type):
    if isinstance(expr, ir.Asm):
        assert isinstance(expr.type_, ir.UnknownType)
        expr.type_ = type_
        return expr

    if isinstance(expr.type_, ir.BuiltinType):
        try:
            assert isinstance(type_, ir.TypeRef)
            assert isinstance(type_.type_, ir.TypeDef)

            from_literal = type_.type_.scope.attrs["__from_literal"]
            if isinstance(from_literal, ir.OverloadedFunction):
                (from_literal,) = list(
                    filter(
                        lambda x: x.macro.func.type_.args[0].type_ == expr.type_, from_literal.overloads  # type:ignore
                    )
                )

            assert isinstance(from_literal, ir.MacroRef)
            from_literal = from_literal.macro
        except KeyError:
            from_literal = None

        # TODO: overloaded
        if from_literal:
            assert isinstance(from_literal, ir.MacroDef)
            arg_type = from_literal.func.type_.args[0].type_
            assert isinstance(arg_type, ir.BuiltinType)
            if expr.type_.name == "__str" and arg_type.name == "__int":
                assert isinstance(expr, ir.StringLiteral)
                # Allow automatic conversion from __str to __int literals on explicit casts
                expr = ir.IntLiteral(expr.info, int.from_bytes(expr.value.encode(), "little"))
            else:
                assert expr.type_.name == arg_type.name  # type:ignore[attr-defined]

            assert type_.has_base_class(from_literal.func.type_.ret_type)
            return ir.ExplicitCast(
                None,
                type_,
                ir.MacroRef(None, from_literal),
                expr,
            )

    # Redundant cast
    if type_ == expr.type_:
        return expr

    # Downcast
    if type_.has_base_class(expr.type_):
        return ir.RefCast(expr.info, type_, expr)

    # Upcast
    if expr.type_.has_base_class(type_):
        return ir.ReinterpretCast(None, type_, expr)

    if isinstance(expr, ir.ReinterpretCast):
        expr.type_ = type_
        return expr

    # TODO: overloaded
    cast_from = type_.get_attr("__cast_from")
    assert isinstance(cast_from, ir.MacroDef)
    assert len(cast_from.func.type_.args) == 1
    assert cast_from.func.type_.args[0].type_ == expr.type_
    return ir.ExplicitCast(None, type_, ir.MacroRef(None, cast_from), expr)


@_check_match_expr_type_result
def match_expr_type(expr: ir.Node, type_: ir.Type):
    assert not isinstance(type_, ir.TypeDef)

    if isinstance(expr, ir.TypeRef):
        match expr.primitive():
            case ir.EnumValueType() as enum if len(enum.field_types) == 0:
                expr = ir.EnumInst(expr.info, expr, enum.discr, [])
            case _:
                raise NotImplementedError(expr)

    assert isinstance(expr, ir.Expr)
    if expr.type_ == type_:
        return expr

    if (
        isinstance(expr.type_, ir.TypeRef)
        and isinstance(expr.type_.type_, ir.TypeDef)
        and expr.type_.has_base_class(type_)
    ):
        return expr

    if isinstance(expr, ir.ReinterpretCast):
        assert isinstance(expr.type_, ir.UnknownType)
        assert not isinstance(type_, ir.UnknownType)
        expr.type_ = type_
        return expr

    assert isinstance(expr, ir.Expr)
    match expr.type_:
        case ir.UnknownType():
            assert isinstance(type_, (ir.TypeRef, ir.UnknownType, ir.VoidType))
            expr.type_ = type_

        case ir.BuiltinType():
            expr = implicit_cast_literal(expr, type_)

        case ir.TypeRef(type_=ir.TypeDef() as expr_type):
            if not expr_type.has_base_class(type_):
                raise Exception(f"Expected {type_}, got {expr.type_}")

        case _:
            if expr.type_ != type_:
                raise Exception(f"Type mismatch: {expr.type_} vs {type_}")

    return expr


def specialize_match(node: ir.Node) -> ir.Node:
    match node:
        case ir.Match():
            assert isinstance(node.match_expr.expr, ir.Expr)
            assert node.match_expr.var.type_ == node.match_expr.expr.type_
            match node.match_expr.expr.type_.primitive():
                case ir.EnumType():
                    cases: list = [ir.MatchCaseEnum.from_case(case) for case in node.cases]
                    return ir.MatchEnum(node.info, node.match_expr, cases, node.scope)
                case ir.IntegralType():
                    cases = []
                    for case in node.cases:
                        if isinstance(case, ir.MatchIntCase):
                            cases.append(case)

                        match case.expr:
                            case ir.ImplicitCast():
                                inlined = inline_macros(case.expr)
                                assert isinstance(inlined, ir.Expr)
                                value = eval_wasm.eval_expr(inlined)
                                assert isinstance(value, int)
                            case ir.IntLiteral():
                                value = case.expr.value
                            case ir.EnumInt():
                                value = case.expr.discr
                            case _:
                                raise NotImplementedError(type(case.expr))

                        cases.append(ir.MatchIntCase(case.info, value, case.scope))
                    return ir.MatchInt(node.info, node.match_expr, cases, node.scope)
                case other:
                    raise NotImplementedError(type(other))

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

        case ir.AstMacroDef():
            return node

        case _:
            return traverse_ir.traverse(check_no_unknown_types, node)
    return node


def inline_macros(node: ir.Node, scope=None) -> ir.Node:
    match node:
        case ir.FunctionDef():
            assert node.scope.func
            return traverse_ir.traverse(inline_macros, node, node.scope)

        case ir.MacroInst():
            # args = [inline_macros(arg, scope) for arg in node.args]
            inlined = traverse_ir.inline(node.macro, scope, node.args)
            inlined = resolve_member_access(inlined)
            inlined = propagate_types(inlined)
            inlined = inline_macros(inlined, scope)
            return inlined

        case ir.ImplicitCast() | ir.ExplicitCast():
            inlined = traverse_ir.inline(node.macro, scope, [node.expr])
            inlined = resolve_member_access(inlined)
            inlined = propagate_types(inlined)
            inlined = inline_macros(inlined, scope)
            return inlined

        case ir.ConstRef():
            return node.const.expr

        case ir.TemplateFor():
            match node.iterable:
                case ir.Call(callee=ir.Builtin(name="__enumerate"), arg=ir.StringLiteral(value=string)):
                    block_name = scope.new_child_name("__inline_for")
                    body = []
                    for i, c in enumerate(string):
                        arg_map: dict[str, ir.Node] = {
                            node.bindings[0].name: ir.IntLiteral(node.bindings[0].info, i),
                            node.bindings[1].name: ir.IntLiteral(node.bindings[1].info, ord(c)),
                        }
                        body.append(traverse_ir.inline_scope(node.body, scope, arg_map))

                    inlined = ir.Block(None, ir.VoidType(None), block_name, ir.Scope(scope, "macro", body))
                    return inline_macros(inlined, scope)
                case _:
                    # raise NotImplementedError
                    return node

        case _:
            return traverse_ir.traverse(inline_macros, node, scope)


def _get_type_dependencies(node, type_: ir.Type | None, depth):
    if type_ and type_.sorting:
        node.sorting = max(node.sorting, type_.sorting + depth)

    match type_:
        case ir.TypeRef():
            _get_type_dependencies(node, type_.type_, depth)

        case ir.TupleType():
            for field in type_.field_types:
                _get_type_dependencies(node, field, depth)

        case ir.EnumType():
            for value in type_.scope.attrs.values():
                if isinstance(value, ir.EnumValueType) and len(value.field_types):
                    for field in value.field_types:
                        _get_type_dependencies(node, field, depth + 1)

        case ir.TypeDef():
            _get_type_dependencies(node, type_.super_, depth + 1)

        case ir.NativeArrayType():
            _get_type_dependencies(node, type_.element_type, depth)

        case ir.IntegralType() | None:
            node.sorting = max(node.sorting, depth)

        case _:
            raise NotImplementedError(type(type_))


def type_sorting(node: ir.Node) -> ir.Node:
    match node:
        case ir.TypeDef():
            if not node.sorting:
                _get_type_dependencies(node, node, 0)

    return traverse_ir.traverse(type_sorting, node)


def done(node: ir.Node) -> ir.Node:
    return node


toplevel_ast_passes: list = [
    register_toplevel_decls,
    register_toplevel_methods,
    check_disallowed_toplevel_decls,
]


ir_passes: list = [
    translate_toplevel_type_decls,
    check_no_untranslated_types,
    translate_function_defs,
    check_no_untranslated_nodes,
    write_tree("inner.ir"),
    instantiate_templates,
    resolve_member_access,
    propagate_types,
    resolve_member_access,
    propagate_types,
    drop_unused_result,
    specialize_match,
    check_no_unknown_types,
    convert_enum_inst,
    inline_macros,
    type_sorting,
    done,
]


def run(prog: ast.Module):
    root_scope = ir.Scope(None, "root")
    root_scope.register_type("__int", ir.BuiltinType("__int"))
    root_scope.register_type("__str", ir.BuiltinType("__str"))
    root_scope.add_method("__enumerate", ir.Builtin("__enumerate"))

    template_arg = ir.TemplateArg(None, "T")
    root_scope.register_type(
        "__native_array",
        ir.TemplateDef(
            None,
            "__native_array",
            ir.NativeArrayType(None, ir.TemplateArgRef(None, template_arg)),
            ir.Scope(root_scope, "__native_array"),
            dict(),
            [template_arg],
        ),
    )
    root_scope.module_scope = root_scope

    module = ir.Module(prog.info, root_scope)
    for pass_ in toplevel_ast_passes:
        print("Pass:", pass_.__name__)
        pass_(prog, module)

    # import pprint
    # pprint.pp(module)

    for pass_ in ir_passes:
        print("Pass:", pass_.__name__)
        module = pass_(module)

    return module
