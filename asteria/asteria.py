import ast
import atexit
import code
import ctypes
import functools
import inspect
import itertools
import re
import readline
import symtable
import weakref
from collections import defaultdict
from pathlib import Path

HISTORY_FILE = Path("~/.asteria-history").expanduser()
AST_CACHE_INDEX = defaultdict(dict)
ASDL_FIELD_SPEC = Path(__file__).parent / "asdl.txt"
ASDL_FIELD_PATTERN = re.compile(r"(\w*)\((.*?)\)")

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


def hash_cache(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        hashid = hash(self)
        caches = AST_CACHE_INDEX[func.__name__]
        if hashid in caches:
            return AST_CACHE_INDEX[func.__name__][hashid]
        result = func(self, *args, **kwargs)
        caches[hashid] = result
        return result

    return wrapper


__to_source = hash_cache(__to_source)


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


@functools.lru_cache
def asdl_parse():
    nodes = ASDL_FIELD_SPEC.read_text().splitlines()
    fields = defaultdict(dict)
    for node in nodes:
        node, declarations = ASDL_FIELD_PATTERN.match(node).groups()
        node = getattr(ast, node)
        for declaration in declarations.split(", "):
            spec, field = declaration.split(" ")
            if spec[-1] == "*":
                fields[node][field] = "[]"
            elif spec[-1] == "?":
                fields[node][field] = "None"
            else:
                fields[node][field] = None
    return fields


def asdl_find_default(node_type, field):
    fields = asdl_parse().get(node_type)
    if fields is None or field not in fields:
        return None
    return fields[field]


def require_parents(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, "parent"):
            raise ValueError("This helper requires a parentized tree.")
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
            f"{field}={asdl_find_default(type(self), field)}"
            for field in self._fields
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

    return compile(self, filename="<ASTERIA>", mode=mode, **kwargs)


@set_method(ast.AST)
@hash_cache
def __ast__to_source(self, strip=True):
    source = __to_source(self)
    if strip:
        source = source.strip()
    return source


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
                    f"Parentized tree finished before reaching to the specified node!"
                ) from exc
            else:
                return

    yield current


@set_method(ast.Module)
def __module__add_global(self, node):
    self.body.insert(0, node)


@set_method(ast.Module)
def __module__get_symbol_table(self, mode="exec", **kwargs):
    return symtable.symtable(self.to_source(), filename="", compile_type=mode)


class AsteriaConsole(code.InteractiveConsole):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_history()

    def init_history(self):
        readline.parse_and_bind("tab: complete")
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(HISTORY_FILE)
            except FileNotFoundError:
                pass
            atexit.register(self.save_history)

    def save_history(self):
        readline.set_history_length(1000)
        readline.write_history_file(HISTORY_FILE)
