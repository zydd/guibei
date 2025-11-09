import os
import sys
import pytest
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser
import compiler
from compiler import ir, codegen


def compile(prog):
    prog = parser.parse_str(prog)
    if not prog:
        raise RuntimeError("Compilation failed: " + prog)

    ir = compiler.semantic_pass(prog)
    print(ir)
    return ir


def test_native_type_alias():
    module = compile("type i32: __native_type<i32>")
    assert "i32" in module.scope.attrs
    assert isinstance(module.scope.attrs["i32"].super_, ir.NativeType)
    wasm = codegen.type_declaration(module.scope.attrs["i32"])
    assert wasm == []


def test_native_type_alias_array():
    module = compile("type float: __native_type<f32>\ntype float_arr: float[]")
    assert "float" in module.scope.attrs
    assert isinstance(module.scope.attrs["float"].super_, ir.NativeType)
    assert "float_arr" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_arr"].super_, ir.ArrayType)
    wasm = codegen.type_declaration(module.scope.attrs["float_arr"])
    assert wasm == [["type", "$module.float_arr", ["array", ["mut", "f32"]]]]


def test_tuple_alias():
    module = compile("type float: __native_type<f32>\ntype float_pair: (float, float)")
    assert "float" in module.scope.attrs
    assert isinstance(module.scope.attrs["float"].super_, ir.NativeType)
    assert "float_pair" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_pair"].super_, ir.TupleType)
    wasm = codegen.type_declaration(module.scope.attrs["float_pair"])
    assert wasm == [["type", "$module.float_pair", ["struct", ["field", "f32"], ["field", "f32"]]]]


def test_tuple_nested():
    module = compile(
        "type float: __native_type<f32>\ntype float_pair: (float, float)\ntype float_mat: (float_pair, float_pair)\n"
    )
    assert "float" in module.scope.attrs
    assert isinstance(module.scope.attrs["float"].super_, ir.NativeType)
    assert "float_pair" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_pair"].super_, ir.TupleType)
    assert "float_mat" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_mat"].super_.field_types[0].primitive(), ir.TupleType)
    assert isinstance(module.scope.attrs["float_mat"].super_.field_types[1].primitive(), ir.TupleType)
    wasm1 = codegen.type_declaration(module.scope.attrs["float_pair"])
    wasm2 = codegen.type_declaration(module.scope.attrs["float_mat"])
    assert wasm1 == [["type", "$module.float_pair", ["struct", ["field", "f32"], ["field", "f32"]]]]
    assert wasm2 == [
        [
            "type",
            "$module.float_mat",
            ["struct", ["field", ["ref", "$module.float_pair"]], ["field", ["ref", "$module.float_pair"]]],
        ]
    ]


def test_void_alias():
    module = compile("type none: ()")
    assert "none" in module.scope.attrs
    assert isinstance(module.scope.attrs["none"].super_, ir.VoidType)
    wasm = codegen.type_declaration(module.scope.attrs["none"])
    assert wasm == []
