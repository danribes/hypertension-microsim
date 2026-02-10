"""Warmup script: precompile juliacall + PythonCall + HypertensionSim during Docker build."""
import os
os.environ["PYTHON_JULIACALL_HANDLE_SIGNALS"] = "yes"

from juliacall import Main as jl

jl.seval('using Pkg; Pkg.activate("/app/julia"; io=devnull)')
jl.seval("using HypertensionSim")
print("juliacall + HypertensionSim precompiled OK")
