import ast
import ctypes
import inspect
import itertools
from functools import partial

try:
    import astpretty
except ImportError:
    __repr = partial(ast.dump, indent=4)
else:
    __repr = partial(astpretty.pformat, show_offsets=False)

try:
    import astor
except ImportError:
    __to_source = ast.unparse
else:
    __to_source = astor.to_source

def set_internal(obj, attr, value):
    globals()[f"__ast__original{attr}"] = getattr(obj, attr)
    setattr(obj, attr, value)

def __ast__repr__(self):
    try:
        return __repr(self)
    except (AttributeError, ValueError):
        return __ast__original__repr__(self)

def __ast__eq__(self, other):
    if not isinstance(other, type(self)):
        return False
    for original_field, other_field in zip(ast.iter_fields(self), ast.iter_fields(other)):
        _, original_value = original_field
        __, other_value = other_field
        if original_value != other_value:
            return False
    else:
        return True

def __ast__init__(self, *args, **kwargs):
    def find_default(field):
        return None

    def generate_arguments():
        return ", ".join(f'{field}={find_default(field)}' for field in self._fields)
    
    signature = inspect._signature_fromstr(inspect.Signature, self, f"({generate_arguments()})")
    arguments = signature.bind(*args, **kwargs)
    arguments.apply_defaults()
    __ast__original__init__(self, **arguments.arguments)

def __ast_compile(self, mode=None, **kwargs):
    if mode is None:
        mode = "eval" if isinstance(self, ast.expr) else "exec"
    return compile(self, filename="<NO_FILE>", mode=mode, **kwargs)

def __ast_to_source(self, strip=True):
    source = to_source(self)
    if strip:
        source = source.strip()
    return source

def __ast_show_source(self):
    print(self.to_source())

set_internal(ast.AST, "__eq__", __ast__eq__)
set_internal(ast.AST, "__init__", __ast__init__)
set_internal(ast.AST, "__repr__", __ast__repr__)
ast.AST.compile = __ast_compile
ast.AST.to_source = __ast_to_source
ast.AST.show_source = __ast_show_source
