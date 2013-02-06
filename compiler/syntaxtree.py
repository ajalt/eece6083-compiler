from collections import namedtuple

BinaryOp = namedtuple('BinaryOp', ['op', 'left', 'right'])
UnaryOp = namedtuple('UnaryOp', ['op', 'operand'])
Num = namedtuple('Num', ['n'])
Name = namedtuple('Name', ['id'])
Call = namedtuple('Call', ['func', 'args'])
Subscript = namedtuple('Subscript', ['name', 'index'])
Str = namedtuple('Str', ['s'])
