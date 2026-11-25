"""Optional CPython AST backend for the supported pure AICL subset."""

from .compiler import CompiledProgram, compile_program

__all__ = ["CompiledProgram", "compile_program"]
