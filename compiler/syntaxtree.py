from collections import namedtuple

BinaryOp = namedtuple('BinaryOp', ['op', 'left', 'right'])
UnaryOp = namedtuple('UnaryOp', ['op', 'operand'])
Num = namedtuple('Num', ['n'])
Name = namedtuple('Name', ['id'])