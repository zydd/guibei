import wasmtime  # type:ignore[import-not-found]
from compiler import ir
from compiler import codegen


def eval_wasm(result_type, expr):
    store = wasmtime.Store()

    module = wasmtime.Module(store.engine, f'(module (func (export "__main") (result {result_type}) {expr}))')
    instance = wasmtime.Instance(store, module, [])

    main_method = instance.exports(store)["__main"]
    return main_method(store)


def eval_expr(expr: ir.Expr):
    (result_type,) = codegen.type_reference(expr.type_)
    (wasm_expr,) = codegen.translate_wasm(expr)
    expr_txt = codegen._wasm_repr_flat(wasm_expr)
    return eval_wasm(result_type, expr_txt)
