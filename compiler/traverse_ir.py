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
            # if len(body) == 1:
            #     body[0].type_ = node.func.type_.ret_type
            #     return body[0]
            return ir.Block(None, node.func.type_.ret_type, block_name, ir.Scope(func_scope, "macro", body))

        case ir.MacroRef():
            return inline(node.macro, func_scope, args)

        case _:
            raise NotImplementedError(type(node))
