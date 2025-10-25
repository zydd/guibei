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
            module.scope.register_type(node.name, ir.EnumType.translate(node, module.scope))
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
        case ir.UntranslatedType():
            return node.translate(scope)
        case ir.TypeRef():
            pass
        case ir.TypeDef():
            return traverse_ir.traverse(translate_toplevel_type_decls, node, node.scope)
        case ir.FunctionDef():
            type_ = translate_toplevel_type_decls(node.type_, scope)
            assert isinstance(type_, ir.FunctionType)
            node.type_ = type_
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
        case ir.FunctionDef():
            for arg in node.type_.args:
                node.scope.register_var(arg.name, ir.VarRef(None, arg))
            node.scope = traverse_ir.traverse(translate_function_defs, node.scope, node.scope)
            return node

        case ir.Untranslated(ast.VarDecl() as var):
            var_type = ir.UntranslatedType(var.type_).translate(scope)
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
                case ir.VarRef():
                    return attr
                case ir.VarDecl() | ir.ArgDecl():
                    return ir.VarRef(id, attr)
                case ir.FunctionDef():
                    return ir.FunctionRef(id, id.name, attr)
                case ir.TypeDef():
                    return ir.TypeRef(id, id.name, attr)
                case _:
                    raise NotImplementedError(attr)

        case ir.WasmExpr():
            terms: list = [translate_function_defs(a, scope) if isinstance(a, ir.Node) else a for a in node.terms]
            node.terms = terms
            return node

        case ir.Untranslated(ast.While() as while_stmt):
            pre_condition = ir.Untranslated(while_stmt.condition)
            loop_scope = ir.Scope(scope, "__while", body=[ir.Untranslated(stmt) for stmt in while_stmt.body])
            loop = ir.Loop(while_stmt, pre_condition, loop_scope)
            return translate_function_defs(loop, loop_scope)

        case ir.Scope():
            node.attrs = traverse_ir.traverse_dict(translate_function_defs, node.attrs, node)
            node.body = traverse_ir.traverse_list(translate_function_defs, node.body, node)
            return node

        case ir.Untranslated():
            return translate_function_defs(node.translate(scope), scope)

        case _:
            return traverse_ir.traverse(translate_function_defs, node, scope)

    raise NotImplementedError(node)


def check_no_untranslated_nodes(node: ir.Node) -> ir.Node:
    match node:
        case ir.Untranslated():
            raise Exception(f"Untranslated node: {node}")
        case _:
            return traverse_ir.traverse(check_no_untranslated_nodes, node)
    return node


def type_declaration(node: ir.Node) -> list:
    match node:
        case ir.NativeType():
            return [node.name]

        case ir.EnumType():
            # TODO: __enum base type
            decls = [ir.WasmExpr(node.ast_node, ["type", f"${node.name}", "(sub (struct (field (ref i31))))"])]
            return decls

        case ir.TypeDef():
            primitive = node.primitive()
            if isinstance(primitive, ir.NativeType):
                return []
            decl = type_declaration(primitive)

            if isinstance(node.super_, ir.TypeRef) and isinstance(node.super_.primitive(), ir.TupleType):
                decl = [["sub", f"${node.super_.name}", *decl]]

            return [ir.WasmExpr(None, ["type", f"${node.name}", *decl])]

        case ir.ArrayType():
            element_primitive = node.element_type.primitive()
            if isinstance(element_primitive, ir.NativeType) and element_primitive.array_packed:
                return [ir.WasmExpr(node.ast_node, ["array", ["mut", element_primitive.array_packed]])]
            else:
                return [ir.WasmExpr(node.ast_node, ["array", ["mut", *type_declaration(element_primitive)]])]

        case ir.TypeRef():
            return type_declaration(node.type_)

    raise NotImplementedError(type(node))


def translate_wasm(node: ir.Node, terms=None) -> ir.WasmExpr:
    match node:
        case ir.Module():
            terms = ["module"]
            # asm_wasm = [translate_wasm(asm) for asm in node.asm]
            # for expr in asm_wasm:
            #     if isinstance(expr, ir.WasmExpr):
            #         terms.extend(expr.terms)
            #     else:
            #         terms.append(expr)

            # breakpoint()
            for type_ in node.scope.attrs.values():
                if not isinstance(type_, ir.Type):
                    continue
                terms.extend(type_declaration(type_))

            return ir.WasmExpr(node.ast_node, terms)

        # case ir.Asm():
        #     assert isinstance(node.terms, ir.WasmExpr)
        #     node.terms = translate_wasm(node.terms)
        #     return node

        case ir.WasmExpr():
            node.terms = [translate_wasm(term) if isinstance(term, ir.Node) else term for term in node.terms]
            return node

        case _:
            return traverse_ir.traverse(translate_wasm, node)

    raise NotImplementedError(node)


toplevel_ast_passes: list = [
    register_toplevel_decls,
    register_toplevel_methods,
    check_unallowed_toplevel_decls,
]


ir_passes: list = [
    translate_toplevel_type_decls,
    check_no_untranslated_types,
    translate_function_defs,
    # check_no_untranslated_nodes,
    translate_wasm,
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
