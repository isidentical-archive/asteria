# Asteria (`Al2O3`)
Missing AST features

## Features
- Repr implementation to every node (uses `astpretty` if it is available, if not fall backs to the `ast.dump`)
- AST Comparisons with other nodes
- Custom initializer with finding default values according to ASDL spec
- Shortcuts for `fix_missing_locations`, `compile` (e.g `ast.parse("2+2").compile()`)
- Unparsing shortcuts, `ast.parse("2+2").to_source()`. It uses astor if its available, if not it fallbacks to the `ast.unparse` interface.
- Parent/Child relationships to nodes
- Helpers functions for mutating tree (like `add_global` method to `Module` nodes which inserts given node at the top of body)
- Symbol table access with `get_symbol_table` method
- and many more...

## Demo
```py
>>> import ast
>>> import asteria
>>> ast.parse("2+2") == ast.parse("2+2")
True
>>> ast.parse("2+2").body[0].value
BinOp(
    left=Constant(value=2, kind=None),
    op=Add(),
    right=Constant(value=2, kind=None),
)
>>> ast.parse("print(2+2)").compile()
<code object <module> at 0x7f2602f21450, file "<ASTERIA>", line 1>
>>> eval(_)
4
>>> ast.parse("import asteria").to_source()
'import asteria'
>>> sample = ast.parse("2+2")
>>> sample.parentize()
>>> sample.body[0].value.left.parent
BinOp(
    left=Constant(value=2, kind=None),
    op=Add(),
    right=Constant(value=2, kind=None),
)
>>> sample.body[0].value.parent
Expr(
    value=BinOp(
        left=Constant(value=2, kind=None),
        op=Add(),
        right=Constant(value=2, kind=None),
    ),
)
>>> some_try = ast.parse("""\
... try:                
...     def x():        
...             print(1)
... finally: pass       
... """)
>>> some_try.parentize()
>>> some_try.body[0].body[0].body[0].value
Call(
    func=Name(id='print', ctx=Load()),
    args=[Constant(value=1, kind=None)],
    keywords=[],
)
>>> len(tuple(some_try.body[0].body[0].body[0].value.until_parented_by(ast.Try)))
3
>>> some_try.add_global(ast.parse("print('lol')").body[0])
>>> print(some_try.to_source())
print('lol')
try:

    def x():
        print(1)
finally:
    pass
```
