import copy
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
    return node


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


def _inline_args(node: ast.Node, args: dict[str, ast.Node]):
    match node:
        case ast.Identifier():
            return args.get(node.name, node)

        case ast.Asm():
            # bypass `traverse_wasm`
            node.terms = _inline_args(node.terms, args)
            return node

        case ast.WasmExpr():
            i = 0
            while i < len(node.terms):
                match node.terms[i]:
                    case ast.Identifier() as id:
                        if id.name in args:
                            arg = args[id.name]
                            if isinstance(arg, ast.Asm):
                                node.terms[i : i + 1] = arg.terms.terms
                                i += len(arg.terms.terms) - 1

                    case ast.Node() as term:
                        node.terms[i] = _inline_args(term, args)

                i += 1
            return node

        case _:
            return traverse(_inline_args, node, args)


def inline(nodes: list[ast.Node], args: dict[str, ast.Node]) -> list[ast.Node]:
    return [_inline_args(copy.deepcopy(stmt), args) for stmt in nodes]
