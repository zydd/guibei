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
                node.name, ir.TypeDef(node, ir.UntranslatedType(node.super_), node.name, ir.Scope(module.scope))
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
            node.scope.attrs = traverse_ir.traverse_dict(
                translate_toplevel_type_decls, node.scope.attrs, scope=node.scope
            )
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
                node.scope.register_var(arg.name, arg)
            node.scope = traverse_ir.traverse(translate_function_defs, node.scope, node.scope)
        case ir.Untranslated(ast.VarDecl() as var):
            var_type = ir.UntranslatedType(var.type_).translate(scope)
            var_decl = ir.VarDecl(var, var.name, var_type)
            scope.register_var(var_decl.name, var_decl)
            if var.init:
                var_init = ir.SetLocal(var.init, ir.VarRef(None, var_decl), ir.Untranslated(var.init))
                return translate_function_defs(var_init, scope)
            else:
                return ir.VoidType(None)

        case ir.Untranslated(ast.Identifier() | ast.TypeIdentifier() | ast.WasmExpr()):
            pass

        case ir.Untranslated(ast.WhileStatement() as while_stmt):
            pre_condition = ir.Untranslated(while_stmt.condition)
            loop_scope = ir.Scope(scope, body=[ir.Untranslated(stmt) for stmt in while_stmt.body])
            loop = ir.Loop(while_stmt, pre_condition, loop_scope)
            return translate_function_defs(loop, scope)

        case ir.Untranslated():
            return translate_function_defs(node.translate(scope), scope)

        case _:
            return traverse_ir.traverse(translate_function_defs, node, scope)
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
]


def run(prog: ast.Module):
    module = ir.Module(prog)
    for pass_ in toplevel_ast_passes:
        print("Pass:", pass_.__name__)
        pass_(prog, module)

    # import pprint
    # pprint.pp(module)

    for pass_ in ir_passes:
        print("Pass:", pass_.__name__)
        module = pass_(module)

    return module
