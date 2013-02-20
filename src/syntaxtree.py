from collections import namedtuple

class Node(object): pass

class Program(namedtuple('Program', ['name', 'decls', 'body']), Node): pass

# Declaration nodes
class VarDecl(namedtuple('VarDecl', ['is_global', 'type', 'name', 'array_length']), Node): pass
class ProcDecl(namedtuple('ProcDecl', ['is_global', 'name', 'params', 'decls', 'body']), Node): pass
class Param(namedtuple('Param', ['var_decl', 'direction']), Node): pass

# Statement nodes
class Assign(namedtuple('Assign', ['target', 'value']), Node): pass
class If(namedtuple('If', ['test', 'body', 'orelse']), Node): pass
class For(namedtuple('For', ['assignment', 'test', 'body']), Node): pass
class Call(namedtuple('Call', ['func', 'args']), Node): pass

# Expression nodes
class BinaryOp(namedtuple('BinaryOp', ['op', 'left', 'right']), Node): pass
class UnaryOp(namedtuple('UnaryOp', ['op', 'operand']), Node): pass
class Num(namedtuple('Num', ['n']), Node): pass
class Name(namedtuple('Name', ['id']), Node): pass
class Subscript(namedtuple('Subscript', ['name', 'index']), Node): pass
class Str(namedtuple('Str', ['s']), Node): pass

class TreeWalker(object):
    def __init__(self):
        self.visit_functions = {}

    def visit(self, node):
        if type(node) in self.visit_functions:
            self.visit_functions[type(node)](node)

    def walk(self, node):
        self.visit(node)

        for field in node:
            if isinstance(field, Node):
                self.walk(field)
            elif isinstance(field, list):
                for child in field:
                    self.walk(field)
