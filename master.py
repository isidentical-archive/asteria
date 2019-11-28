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

FIELD = dict.fromkeys(
    (
        "bases",
        "body",
        "comparators",
        "decorator_list",
        "dims",
        "elts",
        "finalbody",
        "generators",
        "handlers",
        "keys",
        "keywords",
        "names",
        "ops",
        "orelse",
        "targets",
        "type_ignores",
        "values",
    ),
    "[]",
)


def set_method(origin):
    def wrapper(func):
        attr = func.__name__.replace(f"__{origin.__name__.lower()}", "", 1)
        if past := getattr(origin, attr, None):
            globals()[f"__ast__original{attr}"] = past
        else:
            attr = attr[2:]
        setattr(origin, attr, func)
        return func

    return wrapper


@set_method(ast.AST)
def __ast__repr__(self):
    try:
        return __repr(self)
    except (AttributeError, ValueError):
        return __ast__original__repr__(self)


@set_method(ast.AST)
def __ast__eq__(self, other):
    if not isinstance(other, type(self)):
        return False
    for original_field, other_field in zip(
        ast.iter_fields(self), ast.iter_fields(other)
    ):
        _, original_value = original_field
        __, other_value = other_field
        if original_value != other_value:
            return False
    else:
        return True


@set_method(ast.AST)
def __init__(self, *args, **kwargs):
    def generate_arguments():
        return ", ".join(f"{field}={FIELD.get(field)}" for field in self._fields)

    signature = inspect._signature_fromstr(
        inspect.Signature, self, f"({generate_arguments()})"
    )
    arguments = signature.bind(*args, **kwargs)
    arguments.apply_defaults()
    __ast__original__init__(self, **arguments.arguments)


@set_method(ast.AST)
def __ast__compile(self, mode=None, **kwargs):
    if mode is None:
        mode = "eval" if isinstance(self, ast.expr) else "exec"
    return compile(self, filename="<NO_FILE>", mode=mode, **kwargs)


@set_method(ast.AST)
def __ast__to_source(self, strip=True):
    source = __to_source(self)
    if strip:
        source = source.strip()
    return source


@set_method(ast.AST)
def __ast__show_source(self, **kwargs):
    print(self.to_source())
