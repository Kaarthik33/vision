"""Time, maths, apps and shell commands."""

from __future__ import annotations

import ast
import datetime as dt
import math
import operator
import platform
import shutil
import subprocess

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_NAMES = {k: getattr(math, k) for k in ("pi", "e", "tau")}
_FUNCS = {
    k: getattr(math, k)
    for k in ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log10",
              "log2", "exp", "floor", "ceil", "factorial", "radians", "degrees")
}
_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max})


def calculate(expression: str):
    """Safely evaluate an arithmetic expression (no eval)."""

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("exponent too large")
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Name) and node.id in _NAMES:
            return _NAMES[node.id]
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FUNCS and not node.keywords):
            return _FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise ValueError("unsupported expression")

    return ev(ast.parse(expression.replace("^", "**"), mode="eval"))


def open_app(name: str) -> str:
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(f'start "" "{name}"', shell=True)
    elif system == "Darwin":
        subprocess.Popen(["open", "-a", name])
    else:
        exe = shutil.which(name) or shutil.which(name.lower().replace(" ", "-"))
        if not exe:
            return f"Could not find an application called {name}."
        subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Opened {name}."


def run_command(command: str) -> str:
    done = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
    output = (done.stdout + done.stderr).strip()
    return f"exit code {done.returncode}\n{output[:4000]}"


def register(registry) -> None:
    @registry.register("get_time", "Get the current local date and time.")
    def get_time():
        return dt.datetime.now().astimezone().strftime("%A, %d %B %Y, %H:%M %Z")

    registry.register(
        "calculate",
        "Evaluate a maths expression, e.g. '2 * (3 + 4)' or 'sqrt(2) * pi'.",
        {"expression": {"type": "string"}},
        ["expression"],
    )(calculate)

    @registry.register("system_info", "Describe this computer (OS, Python, disk space).")
    def system_info():
        disk = shutil.disk_usage("/")
        return (
            f"{platform.system()} {platform.release()} on {platform.machine()}, "
            f"Python {platform.python_version()}, "
            f"{disk.free // 2**30} GB free of {disk.total // 2**30} GB"
        )

    registry.register(
        "open_app",
        "Open an application on this computer by name.",
        {"name": {"type": "string", "description": "Application name, e.g. 'notepad'"}},
        ["name"],
    )(open_app)

    registry.register(
        "run_command",
        "Run a shell command on this computer and return its output. "
        "The user is asked to confirm first.",
        {"command": {"type": "string"}},
        ["command"],
        dangerous=True,
    )(run_command)
