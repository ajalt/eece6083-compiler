from collections import namedtuple

Program = namedtuple('Program', ['name', 'decls', 'body'])

# Declaration nodes
VarDecl = namedtuple('VarDecl', ['is_global', 'type', 'name', 'array_size'])
ProcDecl = namedtuple('ProcDecl', ['is_global', 'name', 'params', 'var_decls', 'body'])
Param = namedtuple('Param', ['var_decl', 'direction'])

# Statement nodes
Assign = namedtuple('Assign', ['target', 'value'])
If = namedtuple('If', ['test', 'body', 'orelse'])
For = namedtuple('For', ['assignment', 'test', 'body'])

# Expression nodes
BinaryOp = namedtuple('BinaryOp', ['op', 'left', 'right'])
UnaryOp = namedtuple('UnaryOp', ['op', 'operand'])
Num = namedtuple('Num', ['n'])
Name = namedtuple('Name', ['id'])
Call = namedtuple('Call', ['func', 'args'])
Subscript = namedtuple('Subscript', ['name', 'index'])
Str = namedtuple('Str', ['s'])