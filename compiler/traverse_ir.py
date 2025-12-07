import copy
from collections import OrderedDict

from . import ast
from . import ir


def traverse_wasm(func, node, *args, **kwargs):
    return ir.WasmExpr(
        node.ast_node,
        [
            (
                traverse_wasm(func, a, *args, **kwargs)
                if isinstance(a, ir.WasmExpr)
                else func(a, *args, **kwargs) if isinstance(a, ir.Node) else a
            )
            for a in node.terms
        ],
    )


def traverse_dict(func, attr: dict, *args, **kwargs):
    return OrderedDict(filter(lambda x: x[1] is not None, ((k, func(v, *args, **kwargs)) for k, v in attr.items())))


def traverse_list(func, attr: list[ir.Node], *args, **kwargs):
    return list(filter(lambda x: x is not None, (func(a, *args, **kwargs) for a in attr)))


def traverse(func, node: ir.Node, *args, **kwargs):
    assert isinstance(node, ir.Node), type(node)

    if isinstance(node, ir.WasmExpr):
        return traverse_wasm(func, node, *args, **kwargs)

    for attr_name in node:
        attr = node[attr_name]
        if attr_name == "ast_node":
            continue
        match attr:
            case ir.WasmExpr():
                node[attr_name] = traverse_wasm(func, attr, *args, **kwargs)
            case ir.Node():
                node[attr_name] = func(attr, *args, **kwargs)
                assert node[attr_name] is not None
            case list():
                node[attr_name] = traverse_list(func, attr, *args, **kwargs)
            case dict():
                node[attr_name] = traverse_dict(func, attr, *args, **kwargs)
            case str() | int() | None:
                pass
            case _:
                raise NotImplementedError(type(attr))
    return node


def traverse_scoped(func, node: ir.Node, scope):
    assert isinstance(node, ir.Node), type(node)

    match node:
        case ir.WasmExpr():
            return traverse_wasm(func, node, scope)
        case ir.Scope():
            scope = node

    for attr_name in node:
        attr = node[attr_name]
        if attr_name == "ast_node":
            continue
        match attr:
            case ir.WasmExpr():
                node[attr_name] = traverse_wasm(func, attr, scope)
            case ir.Node():
                node[attr_name] = func(attr, scope)
                assert node[attr_name] is not None
            case list():
                node[attr_name] = traverse_list(func, attr, scope)
            case dict():
                node[attr_name] = traverse_dict(func, attr, scope)
            case str() | int() | None:
                pass
            case _:
                raise NotImplementedError(type(attr))
    return node


def _inline_args(node: ir.Node, block_name: str, args: dict[str, ir.Node]):
    match node:
        case ir.ArgRef():
            return args[node.arg.name]

        case ir.VarRef():
            return args[node.var.name]

        case ir.FunctionDef():
            # TODO: handle arg shadowing by lambdas/sub-functions
            raise NotImplementedError

        case ir.FunctionReturn():
            return ir.Break(None, block_name, _inline_args(node.expr, block_name, args))

        case _:
            return traverse(_inline_args, node, block_name, args)


def inline(node: ir.Node, func_scope: ir.Scope | None, args: list[ir.Node]) -> ir.Node:
    match node:
        # case ir.FunctionDef():

        case ir.MacroDef():
            arg_names = [arg.name for arg in node.func.type_.args]
            arg_map: dict = dict(zip(arg_names, args))
            block_name = node.func.scope.new_child_name("__inline." + node.name)
            for var in node.func.scope.attrs.values():
                match var:
                    case ir.VarDecl():
                        var_name = block_name + "." + var.name
                        assert func_scope
                        assert func_scope.func
                        mapped_var = func_scope.register_local(var_name, ir.VarDecl(var.ast_node, var_name, var.type_))
                        arg_map[var.name] = ir.VarRef(None, mapped_var)
            body = [_inline_args(copy.deepcopy(stmt), block_name, arg_map) for stmt in node.func.scope.body]
            if len(body) == 1:
                assert body[0].type_ == node.func.type_.ret_type
                return body[0]
            return ir.Block(None, node.func.type_.ret_type, block_name, ir.Scope(func_scope, "macro", body))

        case ir.MacroRef():
            return inline(node.macro, func_scope, args)

        case _:
            raise NotImplementedError(type(node))


def _inline_template_args(node: ir.Node, args: dict[str, ir.Node]):
    match node:
        case ir.TypeRef():
            if isinstance(node.type_, ir.TemplateArg) and node.name in args:
                return args[node.name]
            return node

        case ir.SelfType():
            return args["Self"]

        case _:
            return traverse(_inline_template_args, node, args)


def instantiate(node: ir.TemplateDef, args: list[ir.TypeRef]) -> ir.TypeDef:
    assert len(args) == len(node.args)
    type_map: dict = dict(zip((arg.name for arg in node.args), args))

    key = tuple(arg.name for arg in args)
    if key in node.instances:
        return node.instances[key]

    if key in node.instances:
        return node.instances[key]

    arg_names = "$" + "$".join([arg.name for arg in args])
    instance_scope = ir.Scope(node.scope, arg_names)

    instance = ir.TypeDef(
        node.ast_node,
        None,
        node.name + arg_names,
        instance_scope,
    )

    type_map["Self"] = ir.TypeRef(None, instance)

    instance.super_ = _inline_template_args(node.super_, type_map) if node.super_ else None
    type_declaration = node.scope.attrs.get("__type_declaration")
    type_declaration = _inline_template_args(type_declaration, type_map) if type_declaration else None
    type_reference = node.scope.attrs.get("__type_reference")
    type_reference = _inline_template_args(type_reference, type_map) if type_reference else None

    if type_declaration:
        instance_scope.attrs["__type_declaration"] = type_declaration

    if type_reference:
        instance_scope.attrs["__type_reference"] = type_reference

    node.instances[key] = instance
    return instance
