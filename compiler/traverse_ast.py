from . import ast


def traverse_wasm(func, node, *args, **kwargs):
    node.terms = [
        (
            traverse_wasm(func, a, *args, **kwargs)
            if isinstance(a, ast.WasmExpr)
            else func(a, *args, **kwargs) if isinstance(a, ast.Node) else a
        )
        for a in node.terms
    ]


def traverse(func, node: ast.Node, *args, **kwargs):
    assert isinstance(node, ast.Node), type(node)
    for attr_name in node:
        attr = node[attr_name]
        match attr:
            case ast.WasmExpr():
                traverse_wasm(func, attr, *args, **kwargs)
            case ast.Node():
                node[attr_name] = func(attr, *args, **kwargs)
            case list():
                node[attr_name] = list(filter(lambda x: x is not None, (func(a, *args, **kwargs) for a in attr)))
            case str() | int() | None:
                pass
            case _:
                raise NotImplementedError(type(attr))
    return node
