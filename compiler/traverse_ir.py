from . import ast
from . import ir


def traverse_wasm(func, node, *args, **kwargs):
    node.terms = [
        (
            traverse_wasm(func, a, *args, **kwargs)
            if isinstance(a, ir.WasmExpr)
            else func(a, *args, **kwargs) if isinstance(a, ir.Node) else a
        )
        for a in node.terms
    ]
    return node


def traverse_dict(func, attr: dict, *args, **kwargs):
    return dict(filter(lambda x: x[1] is not None, ((k, func(v, *args, **kwargs)) for k, v in attr.items())))


def traverse_list(func, attr: list[ir.Node], *args, **kwargs):
    return list(filter(lambda x: x is not None, (func(a, *args, **kwargs) for a in attr)))


def traverse(func, node: ir.Node, *args, **kwargs):
    assert isinstance(node, ir.Node), type(node)
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
