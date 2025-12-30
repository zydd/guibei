import pytest
import textwrap

from common import compile, compile_full
from compiler import codegen, ir


def test_native_type_alias():
    module = compile("type i32\nimpl i32:\n macro __type_reference() -> (): asm: i32")
    assert "i32" in module.scope.attrs
    assert module.scope.attrs["i32"].super_ is None
    wasm = codegen.type_declaration(module.scope.attrs["i32"])
    assert wasm == []


def test_native_type_alias_array():
    module = compile("type float: __integral[f32, f32, array.get]\ntype float_arr: __native_array[float]")
    assert "float" in module.scope.attrs
    assert isinstance(module.scope.attrs["float"].primitive(), ir.IntegralType)
    assert "float_arr" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_arr"].primitive(), ir.NativeArrayType)
    wasm = codegen.type_declaration(module.scope.attrs["float_arr"])
    assert wasm == [["type", "$root.float_arr", ["array", ["mut", "f32"]]]]


def test_tuple_alias():
    module = compile("type float: __integral[f32, f32, array.get]\ntype float_pair: (float, float)")
    assert "float" in module.scope.attrs
    assert isinstance(module.scope.attrs["float"].super_, ir.IntegralType)
    assert "float_pair" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_pair"].super_, ir.TupleType)
    wasm = codegen.type_declaration(module.scope.attrs["float_pair"])
    assert wasm == [
        ["type", "$root.float_pair", ["sub", ["struct", ["field", ["mut", "f32"]], ["field", ["mut", "f32"]]]]]
    ]


def test_tuple_nested():
    module = compile(
        "type float\nimpl float:\n macro __type_reference() -> (): asm: f32\ntype float_pair: (float, float)\ntype float_mat: (float_pair, float_pair)\n"
    )
    assert "float" in module.scope.attrs
    assert module.scope.attrs["float"].super_ is None
    assert "float_pair" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_pair"].super_, ir.TupleType)
    assert "float_mat" in module.scope.attrs
    assert isinstance(module.scope.attrs["float_mat"].super_.field_types[0].primitive(), ir.TupleType)
    assert isinstance(module.scope.attrs["float_mat"].super_.field_types[1].primitive(), ir.TupleType)
    wasm1 = codegen.type_declaration(module.scope.attrs["float_pair"])
    wasm2 = codegen.type_declaration(module.scope.attrs["float_mat"])
    assert wasm1 == [
        ["type", "$root.float_pair", ["sub", ["struct", ["field", ["mut", "f32"]], ["field", ["mut", "f32"]]]]]
    ]
    assert wasm2 == [
        [
            "type",
            "$root.float_mat",
            [
                "sub",
                [
                    "struct",
                    ["field", ["mut", ["ref", "$root.float_pair"]]],
                    ["field", ["mut", ["ref", "$root.float_pair"]]],
                ],
            ],
        ]
    ]


def test_void_alias():
    module = compile("type none")
    assert "none" in module.scope.attrs
    assert module.scope.attrs["none"].super_ is None
    wasm = codegen.type_declaration(module.scope.attrs["none"])
    assert wasm == []


@pytest.mark.parametrize(
    "code",
    [
        "type test\nimpl test:\n func fn(self: Self) -> (): ()",
        "type test\nimpl test:\n func fn(self: test) -> (): ()",
        "type test\nimpl test:\n func fn(self) -> (): ()",
    ],
)
def test_self_type(code):
    module = compile(code)


@pytest.mark.parametrize(
    "code",
    [
        "type other\ntype test\nimpl test:\n func fn(self: other) -> (): ()",
    ],
)
def test_self_type_fail(code):
    with pytest.raises(AssertionError):
        compile(code)


@pytest.mark.parametrize(
    "code",
    [
        'u32.repr(u32 "1234").print()',
    ],
)
def test_str_literal_cast(code):
    assert compile_full(f"func main() -> ():\n" + textwrap.indent(code, "    "))


@pytest.mark.parametrize(
    "code",
    [
        'u32.print("1234")',
    ],
)
def test_str_literal_cast_fail(code):
    with pytest.raises(Exception):
        assert compile_full(f"func main() -> ():\n" + textwrap.indent(code, "    "))
