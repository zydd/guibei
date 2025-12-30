import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

import parser
import compiler
from compiler import ir, codegen
import tempfile
import subprocess


prelude = ""
std_lib_path = os.path.join(base_dir, "lib/prelude")
std_lib_files = [fname for fname in os.listdir(std_lib_path) if fname.endswith(".gi")]
for filename in std_lib_files:
    with open(os.path.join(std_lib_path, filename), "r", encoding="utf8") as f:
        prelude += f.read() + "\n"


def compile(code):
    prog = parser.parse_str(code)
    if not prog:
        raise RuntimeError("Compilation failed: " + prog)

    ir = compiler.semantic_pass(prog)
    print(ir)
    return ir


def compile_full(code):
    prog = parser.parse_str(prelude + code)
    if not prog:
        raise RuntimeError("Compilation failed: " + prog)

    module = compiler.semantic_pass(prog)
    return codegen.translate_wasm(module)


def run(code, exit_ok=None, exit_err=None, stdout=None):
    module = compile_full(code)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".wast", delete=False) as out:
        out.write(codegen.wasm_repr_indented(module))
        out.flush()

        result = subprocess.run(
            ["wasmtime", "-Wgc", out.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if exit_ok is True:
            assert result.returncode == 0, "Execution failed"

        if exit_err is True:
            assert result.returncode != 0, "Execution succeeded while expecting failure"

        if stdout is not None:
            assert result.stdout == stdout, result.stdout

        print(out.name)
        print(result.stdout)
        out.close()
        os.remove(out.name)
        return result
