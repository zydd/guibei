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
            node.scope.types = traverse_ir.traverse_dict(
                translate_toplevel_type_decls, node.scope.types, scope=node.scope
            )
            node.scope.vars = traverse_ir.traverse_dict(
                translate_toplevel_type_decls, node.scope.vars, scope=node.scope
            )
        case ir.UntranslatedType():
            return node.translate(scope)
        case ir.TypeRef():
            pass
        case ir.TypeDef():
            return traverse_ir.traverse(translate_toplevel_type_decls, node, node.scope)
        case ir.FunctionDef():
            node.type_ = translate_toplevel_type_decls(node.type_, scope)
        case _:
            return traverse_ir.traverse(translate_toplevel_type_decls, node, scope)
    return node


def check_no_untranslated_types(node: ir.Node, _scope=None) -> ir.Node:
    match node:
        case ir.UntranslatedType():
            raise Exception(f"Untranslated type: {node}")
        case _:
            return traverse_ir.traverse(check_no_untranslated_types, node, _scope)
    return node

# def local_decls(node, ctx: ir.Module):
#     match node:
#         case ast.FunctionDef():
#             return traverse_ast.traverse(local_decls, node, ctx.new())
#         case ast.ArgDecl():
#             ctx.variables[node.name] = node
#         case ast.Identifier():
#             return ("ArgRef", node.name)
#     return traverse_ast.traverse(local_decls, node, ctx)


toplevel_ast_passes: list = [
    register_toplevel_decls,
    register_toplevel_methods,
    check_unallowed_toplevel_decls,
]


ir_passes: list = [
    translate_toplevel_type_decls,
    check_no_untranslated_types,
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
