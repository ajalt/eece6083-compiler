import itertools

class TreeWalker(object):
    '''Class that will walk an ast and call registered functions for each node found.
    
    To use this class, register functions in the visit_functions and
    leave_functions dictionaries. The key for a callback sound be the class of
    node that the function will be called at, and the value should be a function
    that takes the current node.
    
    Functions registered in visit_functions will called be at a node before
    being called at any children of that node (preorder traversal of the tree).
    A registered function must manually call visit_children if desired. Children
    of nodes with registered funcitons will not be vistied automatically. '''
    def __init__(self):
        self.visit_functions = {}
        self.leave_functions = {}

    def _visit(self, node):
        if type(node) in self.visit_functions:
            self.visit_functions[type(node)](node)
        else:
            self.visit_children(node)
            
    def visit_children(self, node):
        for field in node:
            if isinstance(field, Node):
                self._visit(field)
            elif isinstance(field, list):
                for child in field:
                    self._visit(child)

    def walk(self, node):
        self._visit(node)

class Node(object):
    '''Base class for AST nodes.
    
    This is essentially a mutable version of a namedtuple that's implemented
    with a metaclass instead of the horrifying string template that the stdlib
    uses. All Nodes have an optional 'token' attribute that is not factored into
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
            raise TypeError('%s() takes exactly %s arguments (%s given)' %
                            (self.__class__.__name__, len(self.__slots__) -
                            len(Node.__slots__), len(args)))
        for slot, val in itertools.izip(self.__slots__, args):
           setattr(self, slot, val)
    
    def __iter__(self):
        for slot in self.__slots__:
            if slot != 'token':
                yield getattr(self, slot)
            
    def __len__(self):
        return len(self.__slots__)
            
    def __repr__(self):
        arglist = ', '.join('%s=%r' % (s, getattr(self, s)) for s in self.__slots__ if s != 'token')
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
    def __hash__(self):
        return hash(self.n)

class Name(object):
    __metaclass__ = NodeMeta
    __slots__ = ('id',)
    def __hash__(self):
        return hash(self.id)

class Str(object):
    __metaclass__ = NodeMeta
    __slots__ = ('s',)
    def __hash__(self):
        return hash(self.s)
