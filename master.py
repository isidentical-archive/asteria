import ast
import ctypes
import functools
import inspect
import itertools
import symtable
import weakref

try:
    import astpretty
except ImportError:
    __repr = functools.partial(ast.dump, indent=4)
else:
    __repr = functools.partial(astpretty.pformat, show_offsets=False)

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
        if not hasattr(func, "name"):
            if hasattr(func, "fget"):
                func = func.fget
            elif hasattr(func, "__func__"):
                func = func.__func__

        attr = func.__name__.replace(f"__{origin.__name__.lower()}", "", 1)
        if past := getattr(origin, attr, None):
            globals()[f"__ast__original{attr}"] = past
        else:
            attr = attr[2:]
        setattr(origin, attr, func)
        return func

    return wrapper


def require_parents(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, "parent"):
            raise ValueError(
                "Tree should be parentized before a until_parented_by action happended!"
            )
        return func(self, *args, **kwargs)

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
        return ", ".join(
            f"{field}={FIELD.get(field)}" for field in self._fields
        )

    signature = inspect._signature_fromstr(
        inspect.Signature, self, f"({generate_arguments()})"
    )
    arguments = signature.bind(*args, **kwargs)
    arguments.apply_defaults()
    __ast__original__init__(self, **arguments.arguments)


@set_method(ast.AST)
def __ast__fix_missing_locations(self):
    ast.fix_missing_locations(self)


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


@set_method(ast.AST)
def __ast__parentize(self, weak=False):
    for parent in ast.walk(self):
        for children in ast.iter_child_nodes(parent):
            if weak:
                ref = weakref.ref(parent)
            else:
                ref = parent
            children.parent = ref


@set_method(ast.AST)
@require_parents
def __ast__until_parented_by(self, node_type, strict=False):
    current = self.parent
    while not isinstance(current, node_type):
        yield current
        try:
            current = current.parent
        except AttributeError as exc:
            if strict:
                raise ValueError(
                    f"Parentized tree finished before reaching specified node!"
                ) from exc
            else:
                return

    yield current


@set_method(ast.Module)
def __module__add_global(self, node):
    self.body.insert(node, 0)


@set_method(ast.Module)
def __module__get_symbol_table(self, mode="exec", **kwargs):
    return symtable.symtable(self.to_source(), filename="", compile_type=mode)
