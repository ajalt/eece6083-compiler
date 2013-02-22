import itertools

class Node(object):
    '''Baseclass for AST nodes.
    
    This is exestially a mutable version of a namedtuple that's implemented with
    a metaclass isntead of the horrific string templating that the stdlib uses.
    All Nodes have an optional 'token' attribute that is not factored into
    equality comparisons. '''
    __hash__ = None
    __slots__ = ('token',)
    
    def __init__(self, *args, **kwargs):
        if 'token' in kwargs:
            self.token = kwargs['token']
            del kwargs['token']
        else:
            self.token = None
        if kwargs:
            raise TypeError('Invalid keyword arguments: %r' % kwargs.keys())
        if len(args) != len(self.__slots__) - len(Node.__slots__):
            raise TypeError('__init__() takes exactly %s arguments (%s given)' %
                            (len(args), len(self.__slots__) - len(Node.__slots__)))
        for slot, val in itertools.izip(self.__slots__, args):
           setattr(self, slot, val)
    
    def __iter__(self):
        for slot in self.__slots__:
            if slot != 'token':
                yield getattr(self, slot)
            
    def __len__(self):
        return len(self.__slots__)
            
    def __repr__(self):
        arglist = ', '.join('%s=%r' % (s, getattr(self, s)) for s in self.__slots__)
        return '%s(%s)' %(self.__class__.__name__, arglist)
    
    def __eq__(self, other):
        '''Compare two nodes and return True if all fields are equal, disregarding tokens.'''
        if not isinstance(other, Node):
           return False
        if len(self) != len(other):
           return False
        for a, b in itertools.izip_longest(self, other):
           if a != b:
              return False
        return True
    
    def __ne__(self, other):
        return not (self == other)
   

# We have to use a metaclass here instead of inheritance since there's no easy
# way for a child class to extend it's parent's __slots__.
class NodeMeta(type):
    def __new__(mcls, name, bases, dict_):
       dict_['__slots__'] += Node.__slots__
       return type(name, (Node,) + bases, dict_)

class Program(object):
    __metaclass__ = NodeMeta
    __slots__ = ('name', 'decls', 'body')


# Declaration nodes
class VarDecl(object):
    __metaclass__ = NodeMeta
    __slots__ = ('is_global', 'type', 'name', 'array_length')

class ProcDecl(object):
    __metaclass__ = NodeMeta
    __slots__ = ('is_global', 'name', 'params', 'decls', 'body')

class Param(object):
    __metaclass__ = NodeMeta
    __slots__ = ('var_decl', 'direction')


# Statement nodes
class Assign(object):
    __metaclass__ = NodeMeta
    __slots__ = ('target', 'value')

class If(object):
    __metaclass__ = NodeMeta
    __slots__ = ('test', 'body', 'orelse')

class For(object):
    __metaclass__ = NodeMeta
    __slots__ = ('assignment', 'test', 'body')

class Call(object):
    __metaclass__ = NodeMeta
    __slots__ = ('func', 'args')


# Expression nodes
class BinaryOp(object):
    __metaclass__ = NodeMeta
    __slots__ = ('op', 'left', 'right')

class UnaryOp(object):
    __metaclass__ = NodeMeta
    __slots__ = ('op', 'operand')

class Subscript(object):
    __metaclass__ = NodeMeta
    __slots__ = ('name', 'index')

class Num(object):
    __metaclass__ = NodeMeta
    __slots__ = ('n',)

class Name(object):
    __metaclass__ = NodeMeta
    __slots__ = ('id',)

class Str(object):
    __metaclass__ = NodeMeta
    __slots__ = ('s',)


class TreeWalker(object):
    def __init__(self):
        self.visit_functions = {}
        self.leave_functions = {}

    def visit(self, node):
        if type(node) in self.visit_functions:
            self.visit_functions[type(node)](node)
            
    def leave(self, node):
        if type(node) in self.leave_functions:
            self.leave_functions[type(node)](node)

    def walk(self, node):
        self.visit(node)

        for field in node:
            if isinstance(field, Node):
                self.walk(field)
            elif isinstance(field, list):
                for child in field:
                    self.walk(field)
                    
        self.leave(node)
