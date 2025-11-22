from compiler import ast
from compiler import ir
from compiler import traverse_ast
from compiler import traverse_ir


def register_toplevel_decls(node: ast.Node, module: ir.Module):
    match node:
        case ast.Module():
            traverse_ast.traverse(register_toplevel_decls, node, module)
        case ast.TypeDef():
            module.scope.register_type(
                node.name,
                ir.TypeDef(node, ir.UntranslatedType(node.super_), node.name, ir.Scope(module.scope, node.name)),
            )
        case ast.EnumType():
            enum_type = ir.EnumType.translate(node, module.scope)
            module.scope.register_type(node.name, enum_type)
            for i, val in enumerate(node.values):
                enum_type.scope.register_type(val.name, ir.EnumValueType.translate(enum_type, i, val))
        case ast.FunctionDef():
            module.scope.register_var(node.name, ir.FunctionDef.translate(node, module.scope))
        case ast.Asm():
            module.add_asm(ir.Untranslated(node))
        case _:
            return node


def register_toplevel_methods(node: ast.Node, module: ir.Module):
    match node:
        case ast.Module():
            traverse_ast.traverse(register_toplevel_methods, node, module)
        case ast.TypeImpl():
            type_ = module.scope.lookup_type(node.type_name)
            assert isinstance(type_, ir.TypeDef)
            for method in node.methods:
                assert isinstance(method, ast.FunctionDef)
                type_.add_method(method.name, ir.FunctionDef.translate(method, type_.scope))
        case _:
            return node


def check_unallowed_toplevel_decls(node: ast.Node, module: ir.Module):
    assert isinstance(node, ast.Module)
    assert len(node.stmts) == 0, f"{type(node.stmts[0]).__name__} not allowed as a top level declaration"


def translate_toplevel_type_decls(node: ir.Node, scope=None) -> ir.Node:
    match node:
        case ir.Module():
            node.scope.attrs = traverse_ir.traverse_dict(translate_toplevel_type_decls, node.scope.attrs, node.scope)

        case ir.UntranslatedType(ast.ArrayType() as ast_node):
            tr_type = translate_toplevel_type_decls(ir.UntranslatedType(ast_node.element_type), scope)
            assert isinstance(tr_type, ir.Type)
            return ir.ArrayType(ast_node, tr_type)

        case ir.UntranslatedType(ast.TupleType() as ast_node):
            if not ast_node.field_types:
                return ir.VoidType(ast_node)

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
                return ir.NamedTupleType(ast_node, field_types, field_names)
            else:
                return ir.TupleType(ast_node, field_types)

        case ir.UntranslatedType(ast.TypeIdentifier() | ast.Identifier() as ast_node):
            type_: ir.Type = scope.lookup_type(ast_node.name)
            return ir.TypeRef(node.ast_node, type_)

        case ir.UntranslatedType(ast.GetAttr(obj=ast.TypeIdentifier() as obj, attr=str()) as ast_node):
            type_ = scope.lookup_type(obj.name)
            assert isinstance(type_, ir.TypeDef)
            member = type_.scope.attrs[ast_node.attr]
            assert isinstance(member, ir.TypeDef)
            return ir.TypeRef(ast_node, member)

        case ir.UntranslatedType():
            return node.translate(scope)

        case ir.TypeRef():
            pass

        case ir.TypeDef():
            return traverse_ir.traverse(translate_toplevel_type_decls, node, node.scope)

        case ir.FunctionDef():
            tr_type = translate_toplevel_type_decls(node.type_, scope)
            assert isinstance(tr_type, ir.FunctionType)
            node.type_ = tr_type

        case _:
            return traverse_ir.traverse(translate_toplevel_type_decls, node, scope)
    return node


def check_no_untranslated_types(node: ir.Node, scope=None) -> ir.Node:
    match node:
        case ir.UntranslatedType():
            raise Exception(f"Untranslated type: {node}")
        case _:
            return traverse_ir.traverse(check_no_untranslated_types, node, scope)
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
                node.scope.register_var(arg.name, ir.VarRef(None, arg))

            node.scope = traverse_ir.traverse(translate_function_defs, node.scope, node.scope)

            # TODO: Can't do this transformation here because we might need to drop the result of expr if the function returns void
            # if node.scope.body and isinstance(node.scope.body[-1], ir.Expr):
            #     node.scope.body[-1] = ir.FunctionReturn(None, ir.FunctionRef(None, node), node.scope.body[-1])

            return node

        case ir.Untranslated(ast.VarDecl() as var):
            var_type = translate_toplevel_type_decls(ir.UntranslatedType(var.type_), scope)
            assert isinstance(var_type, ir.Type)
            var_decl = ir.VarDecl(var, var.name, var_type)
            scope.register_local(var_decl.name, var_decl)
            if var.init:
                var_init = ir.SetLocal(var.init, ir.VarRef(None, var_decl), ir.Untranslated(var.init))
                return translate_function_defs(var_init, scope)
            else:
                return ir.VoidType(None)

        case ir.Untranslated(ast.Identifier() | ast.TypeIdentifier() as id):
            attr = scope.lookup(id.name)
            if isinstance(id, ast.TypeIdentifier):
                assert isinstance(attr, ir.Type)

            match attr:
                case ir.VarRef() | ir.TypeRef():
                    return attr
                case ir.VarDecl() | ir.ArgDecl():
                    return ir.VarRef(id, attr)
                case ir.FunctionDef():
                    return ir.FunctionRef(id, attr)
                case ir.TypeDef():
                    return ir.TypeRef(id, attr)
                case _:
                    raise NotImplementedError(attr)

        case ir.Untranslated(ast.TupleExpr() as ast_node):
            if len(ast_node.field_values) == 1:
                return translate_function_defs(ir.Untranslated(ast_node.field_values[0]), scope)
            else:
                fields: list = [
                    translate_function_defs(ir.Untranslated(field), scope) for field in ast_node.field_values
                ]
                assert all(isinstance(field, ir.Expr) for field in fields)
                return ir.TupleInst(ast_node, ir.UnknownType(), fields)

        case ir.WasmExpr():
            terms: list = [translate_function_defs(a, scope) if isinstance(a, ir.Node) else a for a in node.terms]
            node.terms = terms
            return node

        case ir.Untranslated(ast.While() as while_stmt):
            pre_condition = ir.Untranslated(while_stmt.condition)
            loop_scope = ir.Scope(scope, "__while", body=[ir.Untranslated(stmt) for stmt in while_stmt.body])
            loop = ir.Loop(while_stmt, pre_condition, loop_scope)
            return translate_function_defs(loop, loop_scope)

        case ir.GetTupleItem():
            expr = translate_function_defs(node.expr, scope)
            assert isinstance(expr, ir.Expr)
            node.expr = expr
            assert isinstance(node.type_, ir.UnknownType)
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

        case ir.GetAttr():
            node.obj = translate_function_defs(node.obj, scope)
            match node.obj:
                case ir.TypeRef():
                    assert isinstance(node.obj.type_, ir.TypeDef)
                    attr = node.obj.type_.scope.lookup(node.attr)
                    match attr:
                        case ir.FunctionDef():
                            if isinstance(node.obj.primitive(), ir.EnumValueType) and attr.type_.args[0].name == "self":
                                return ir.BoundMethod(
                                    node.ast_node,
                                    ir.UnknownType(),
                                    ir.FunctionRef(None, attr),
                                    ir.TupleInst(
                                        node.obj.ast_node, node.obj, [ir.IntLiteral(None, node.obj.primitive().discr)]
                                    ),
                                )
                            else:
                                return ir.FunctionRef(node.ast_node, attr)
                        case ir.TypeRef():
                            return attr
                        case ir.AsmType():
                            return attr
                        case ir.EnumValueType():
                            return ir.TypeRef(None, attr)
                        case _:
                            raise NotImplementedError(type(attr))
                case ir.Expr():
                    assert isinstance(node.obj.type_, ir.TypeRef)

                    obj_type_prim = node.obj.type_.primitive()
                    if isinstance(obj_type_prim, ir.NamedTupleType) and node.attr in obj_type_prim.field_names:
                        field = obj_type_prim.field_names.index(node.attr)
                        return ir.GetTupleItem(node.ast_node, node.obj, field, obj_type_prim.field_types[field])
                    else:
                        assert isinstance(node.obj.type_.type_, ir.TypeDef)
                        method = node.obj.type_.type_.scope.lookup(node.attr)
                        assert isinstance(method, ir.FunctionDef)
                        if method.type_.args[0].name == "self":
                            return ir.BoundMethod(
                                node.ast_node, ir.UnknownType(), ir.FunctionRef(None, method), node.obj
                            )
                        else:
                            raise RuntimeError("Calling static method from object")
                            # return method
                case _:
                    # TODO
                    breakpoint()
                    return node
                    raise NotImplementedError(type(node.obj))

        case ir.Call():
            node.callee = translate_function_defs(node.callee, scope)
            node.args = traverse_ir.traverse_list(translate_function_defs, node.args, scope)
            match node.callee:
                case ir.FunctionRef():
                    assert isinstance(node.callee.func.type_.ret_type, (ir.TypeRef, ir.VoidType))
                    return ir.FunctionCall(node.ast_node, node.callee.func.type_.ret_type, node.callee, node.args)
                case ir.BoundMethod():
                    assert isinstance(node.callee.func.func.type_.ret_type, (ir.TypeRef, ir.VoidType))
                    return ir.FunctionCall(
                        node.ast_node,
                        node.callee.func.func.type_.ret_type,
                        node.callee.func,
                        [node.callee.obj] + node.args,
                    )
                case ir.TypeRef():
                    match node.callee.primitive():
                        case ir.NativeType():
                            # TODO: generalize
                            assert len(node.args) == 1
                            assert isinstance(node.args[0], ir.IntLiteral)
                            return ir.Asm(
                                node.ast_node,
                                ir.WasmExpr(node.ast_node, ["i32.const", node.args[0].value]),
                                node.callee,
                            )
                        case ir.EnumValueType() as enum_val:
                            assert all(isinstance(arg, ir.Expr) for arg in node.args)
                            args: list = node.args
                            return ir.TupleInst(
                                node.ast_node, node.callee, [ir.IntLiteral(None, enum_val.discr)] + args
                            )
                        case ir.TupleType():
                            assert all(isinstance(arg, ir.Expr) for arg in node.args)
                            tuple_args: list = node.args
                            return ir.TupleInst(node.ast_node, node.callee, tuple_args)

                        case _:
                            raise NotImplementedError(node.callee)
                case _:
                    raise NotImplementedError(type(node.callee))

        case ir.Scope():
            node.attrs = traverse_ir.traverse_dict(translate_function_defs, node.attrs, node)
            node.body = traverse_ir.traverse_list(translate_function_defs, node.body, node)
            return node

        case ir.Assignment():
            node.lvalue = translate_function_defs(node.lvalue, scope)
            expr = translate_function_defs(node.expr, scope)
            assert isinstance(expr, ir.Expr)
            node.expr = expr
            if isinstance(node.lvalue, ir.GetItem):
                return ir.SetItem(node.ast_node, node.lvalue.expr, node.lvalue.idx, expr)
            else:
                return node

        case ir.MatchCaseEnum():
            node.enum = translate_function_defs(node.enum, scope)
            assert isinstance(node.enum, ir.TypeRef)
            assert isinstance(node.enum.type_, ir.EnumValueType)
            for i in range(len(node.args)):
                assert isinstance(node.args[i], ir.Untranslated)
                arg_type = node.enum.type_.fields.field_types[i + 1]
                assert isinstance(arg_type, ir.TypeRef)
                match node.args[i].ast_node:
                    case ast.Placeholder() as placeholder:
                        node.args[i] = ir.Placeholder(placeholder, arg_type)
                    case ast.Identifier() as id:
                        var_decl = ir.VarDecl(id, id.name, arg_type)
                        node.scope.register_local(id.name, var_decl)
                        node.args[i] = ir.VarRef(None, var_decl)
                    case _:
                        raise NotImplementedError
            node_scope = translate_function_defs(node.scope, scope)
            assert isinstance(node_scope, ir.Scope)
            node.scope = node_scope
            return node

        case ir.Untranslated():
            return translate_function_defs(node.translate(scope), scope)

        case _:
            return traverse_ir.traverse(translate_function_defs, node, scope)

    raise NotImplementedError(type(node))


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

        case ir.FunctionReturn():
            assert isinstance(node.func.func.type_.ret_type, (ir.TypeRef | ir.VoidType))
            node.expr = propagate_types(match_expr_type(node.expr, node.func.func.type_.ret_type))

        case ir.FunctionCall():
            assert len(node.args) == len(node.func.func.type_.args)
            node.args = [
                propagate_types(match_expr_type(arg, arg_decl.type_))
                for arg, arg_decl in zip(node.args, node.func.func.type_.args)
            ]

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
                        expr = propagate_types(node.scope.body[-1])
                        assert not isinstance(expr.type_, ir.UnknownType)
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

        case ir.SetLocal():
            node.expr = propagate_types(match_expr_type(node.expr, node.var.type_))

        case ir.SetItem():
            node.expr = propagate_types(node.expr)
            node.idx = propagate_types(node.idx)
            node.value = propagate_types(match_expr_type(node.value, node.expr.type_.primitive().element_type))

        case ir.GetItem():
            node.type_ = node.expr.type_.primitive().element_type
            node.expr = propagate_types(node.expr)
            # TODO: match numeric type
            node.idx = propagate_types(node.idx)

        case ir.Match():
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
                        assert isinstance(node.match_expr, ir.Assignment)
                        assert isinstance(node.match_expr.expr, ir.Expr)
                        case.expr = propagate_types(match_expr_type(case.expr, node.match_expr.expr.type_))
                        case.scope = propagate_types(case.scope)

                    case _:
                        raise NotImplementedError(case)

        case _:
            return traverse_ir.traverse(propagate_types, node)

    return node


def match_expr_type(expr: ir.Node, type_: ir.Type):
    if isinstance(expr, ir.TypeRef):
        match expr.primitive():
            case ir.EnumValueType() as enum if len(enum.fields.field_types) == 1:
                expr = ir.TupleInst(expr.ast_node, expr, [ir.IntLiteral(None, enum.discr)])
            case _:
                raise NotImplementedError(expr)

    assert isinstance(expr, ir.Expr)
    match expr.type_:
        case ir.UnknownType():
            assert isinstance(type_, (ir.TypeRef, ir.UnknownType, ir.VoidType))
            expr.type_ = type_
        case ir.AstType(name="__int_literal"):
            assert isinstance(type_.primitive(), ir.NativeType)
        case ir.AstType(name="__string_literal"):
            assert isinstance(type_.primitive(), ir.ArrayType)
            assert isinstance(expr, ir.StringLiteral)
            assert isinstance(expr.temp_var.type_, ir.UnknownType)
            assert isinstance(expr.temp_var.var.type_, ir.UnknownType)
            assert isinstance(type_, ir.TypeRef)
            expr.temp_var.type_ = expr.temp_var.var.type_ = type_
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
            assert isinstance(node.match_expr, ir.Assignment)
            assert isinstance(node.match_expr.lvalue, ir.VarRef)
            assert isinstance(node.match_expr.expr, ir.Expr)
            node.match_expr.lvalue.var.type_ = node.match_expr.expr.type_
            if isinstance(node.match_expr.expr.type_.primitive(), ir.EnumType):
                cases = [ir.MatchCaseEnum.from_case(case) for case in node.cases]
                return ir.MatchEnum(node.ast_node, node.match_expr, cases, node.scope)
            else:
                raise NotImplementedError

        case _:
            return traverse_ir.traverse(specialize_match, node)
    return node


def check_no_unknown_types(node: ir.Node) -> ir.Node:
    match node:
        case ir.UnknownType():
            raise Exception(f"Unknown type: {node}")

        case ir.VarRef():
            # TODO: fix VarRef type update
            assert isinstance(node.var.type_, ir.TypeRef)
            node.type_ = node.var.type_
            check_no_unknown_types(node.type_)

        case _:
            return traverse_ir.traverse(check_no_unknown_types, node)
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
    propagate_types,
    specialize_match,
    check_no_unknown_types,
]


def run(prog: ast.Module):
    module = ir.Module(prog, ir.Scope(None, "module"))
    for pass_ in toplevel_ast_passes:
        print("Pass:", pass_.__name__)
        pass_(prog, module)

    # import pprint
    # pprint.pp(module)

    for pass_ in ir_passes:
        print("Pass:", pass_.__name__)
        module = pass_(module)

    return module
