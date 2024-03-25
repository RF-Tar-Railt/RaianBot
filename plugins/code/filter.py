# Check whether the input text is a valid python code.
# Invalid code includes:
# - module `os`, `sys`, `pathlib`
# - function `exit`
# - function `open`
# - function `eval`, `exec`, `compile`
# - loop `while`
# - getattr `__dict__`, `__globals__` or `__builtins__`
# - operator `**` with large exponent

import ast


def check(lines: list[str]):
    code = "\n".join(lines)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ("exit", "open", "eval", "exec", "compile"):
                    return False
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ("__dict__", "__globals__", "__builtins__"):
                    return False
        elif isinstance(node, ast.Attribute):
            if node.attr in ("__dict__", "__globals__", "__builtins__"):
                return False
        elif isinstance(node, ast.Import):
            for name in node.names:
                if name.name in ("os", "sys", "pathlib"):
                    return False
        elif isinstance(node, ast.ImportFrom):
            if node.module in ("os", "sys", "pathlib"):
                return False
        elif isinstance(node, ast.While):
            return False
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow):
                if isinstance(node.right, ast.Constant):
                    value = node.right.value
                    if isinstance(value, (int, float)) and value > 3:
                        return False
    return True


if __name__ == "__main__":
    print(check(["[].__class__.__subclasses__()[0].__init__.__globals__"]))
    print(check(["eval('1+1')"]))
    print(check(["exec('1+1')"]))
    print(check(["while True: pass"]))
    print(check(["2**3"]))
    print(check(["2**100"]))
    print(
        check(
            [
                "[ x.__init__.__globals__ for x in "
                '.__class__.__base__.__subclasses__() if "wrapper" not in str(x.__init__) and "builtins" in x.__init__.__globals__ ]'  # noqa: E501
            ]
        )
    )
