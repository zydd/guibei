import os
import sys
import pytest
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser
import compiler
import compiler.ast


def compile(prog):
    prog = parser.parse_str(prog)
    if not prog:
        sys.exit(1)

    comp = compiler.CompilePass()
    comp.compile(prog)
    print(comp.wasm)
    return comp


def test_native_type_alias():
    comp = compile("type i32: __native_type<i32>")
    assert "i32" in comp.root_context.types
    assert isinstance(comp.root_context.types["i32"].super_, compiler.ast.NativeType)
    assert comp.wasm == []


def test_native_type_alias_array():
    comp = compile("type float: __native_type<f32>\ntype float_arr: float[]")
    assert "float" in comp.root_context.types
    assert isinstance(comp.root_context.types["float"].super_, compiler.ast.NativeType)
    assert "float_arr" in comp.root_context.types
    assert isinstance(comp.root_context.types["float_arr"], compiler.ast.ArrayType)
    assert str(comp.wasm[0]) == "(type $float_arr (array (mut f32)))"


def test_tuple_alias():
    comp = compile("type float: __native_type<f32>\ntype float_pair: (float, float)")
    assert "float" in comp.root_context.types
    assert isinstance(comp.root_context.types["float"].super_, compiler.ast.NativeType)
    assert "float_pair" in comp.root_context.types
    assert isinstance(comp.root_context.types["float_pair"], compiler.ast.TupleType)
    assert str(comp.wasm[0]) == "(type $float_pair (struct (field f32) (field f32)))"


def test_tuple_nested():
    comp = compile(
        "type float: __native_type<f32>\ntype float_pair: (float, float)\ntype float_mat: (float_pair, float_pair)\n"
    )
    assert "float" in comp.root_context.types
    assert isinstance(comp.root_context.types["float"].super_, compiler.ast.NativeType)
    assert "float_pair" in comp.root_context.types
    assert isinstance(comp.root_context.types["float_pair"], compiler.ast.TupleType)
    assert "float_mat" in comp.root_context.types
    assert isinstance(comp.root_context.types["float_mat"].field_types[0].type_, compiler.ast.TupleType)
    assert isinstance(comp.root_context.types["float_mat"].field_types[1].type_, compiler.ast.TupleType)
    assert str(comp.wasm[1]) == "(type $float_mat (struct (field (ref $float_pair)) (field (ref $float_pair))))"


def test_void_alias():
    comp = compile("type none: ()")
    assert "none" in comp.root_context.types
    assert isinstance(comp.root_context.types["none"], compiler.ast.VoidType)
    assert comp.wasm == []
