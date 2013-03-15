import itertools
import sys
import ast
import types


class TreeWalker(object):
    '''Class that will walk an ast and call registered functions for each node found.
    
    To use this class, register functions in the visit_functions and
    leave_functions dictionaries. The key for a callback sound be the class of
    node that the function will be called at, and the value should be a function
    that takes the current node.
    
    Functions registered in visit_functions will called be at a node before
    being called at any children of that node (preorder traversal of the tree).
    A registered function must manually call visit_children if desired. Children
    of nodes with registered functions will not be visited automatically. '''
    def __init__(self):
        self.visit_functions = {}
        self.leave_functions = {}

    def _visit(self, node):
        if type(node) in self.visit_functions:
            return self.visit_functions[type(node)](node)
        elif isinstance(node, Node):
            return self.visit_children(node)
        return node
            
    def visit_children(self, node):
        for field in node:
            if isinstance(field, Node):
                self._visit(field)
            elif isinstance(field, list):
                for child in field:
                    self._visit(child)

    def walk(self, node):
        return self._visit(node)
        
class TreeMutator(TreeWalker):
    '''Class that will walk an AST and mutate the tree in place.
    
    Registered visit_functions should return a value that will replace the node
    they are visiting. If they return None, the node will be removed from the
    tree.'''
    def __init__(self):
        super(TreeMutator, self).__init__()
        self.modified_tree = False
    
    def visit_children(self, node):
        for field_name, original_field in node.iter_fields():
            if isinstance(original_field, Node):
                new_field = self._visit(original_field)
                setattr(node, field_name, new_field)
                if original_field != new_field:
                    self.modified_tree = True
            elif isinstance(original_field, list):
                new_field = []
                for child in original_field:
                    value = self._visit(child)
                    if value is not None:
                        if isinstance(value, list):
                            new_field.extend(value)
                        else:
                            new_field.append(value)
                setattr(node, field_name, new_field)
                if original_field != new_field:
                    self.modified_tree = True
        return node
    
def dump_tree(node, indent_level=1, output=sys.stdout.write):
    indent = '  ' * indent_level
    output(node.__class__.__name__)
    output('(')
    
    # If any fields are nodes, print each field on a separate line
    if any(isinstance(field, (list, Node)) for field in node):
        for i, (name, field) in enumerate(node.iter_fields()):
            if i:
                output(',')
            output('\n')
            output(indent)
            output(name)
            output('=')
            if isinstance(field, Node):
                dump_tree(field, indent_level+1)
            elif isinstance(field, list):
                output('[')
                for j, child in enumerate(field):
                    if j:
                        output(',')
                    output('\n' + indent + '  ')
                    if isinstance(child, Node):
                        dump_tree(child, indent_level+2)
                    else:
                        output(repr(child))
                    
                output(']')
            else:
                output(repr(field))
    # Otherwise, print all the fields on one line
    else:
        output(', '.join(repr(field) for field in node))
    output(')')
            
class Node(object):
    '''Base class for AST nodes.
    
    This is essentially a mutable version of a namedtuple that's implemented
    with a metaclass instead of the horrifying string template that the stdlib
    uses. All Nodes have an optional 'token' attribute that is not factored into
    equality comparisons. '''
    __hash__ = None
    
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
    
    def iter_fields(self):
        '''Iterate over tuples of (field_name, field)'''
        for slot in self.__slots__:
            if slot != 'token':
                yield slot, getattr(self, slot)
   

class NodeMeta(type):
    def __new__(mcls, name, bases, dict_):
        dict_['__slots__'] += ('token',)
        
        # Warning: deep magicks ahead
        
        # We use Python's AST to dynamically create a python module
        # that has a single function definition in it. 
        f = ast.FunctionDef(name='__init__', decorator_list=[])
        
        # The function has the parameter self, one required parameter for
        # each slot, and the optional token parameter.
        args = ([ast.Name(id='self', ctx=ast.Param())] +
                [ast.Name(id=slot, ctx=ast.Param()) for slot in dict_['__slots__']])
        f.args = ast.arguments(args=args, vararg=None, kwarg=None,
                               defaults=[ast.Name(id='None', ctx=ast.Load())])
        
        # The body of the function sets instance variables for each parameter.
        f.body = [
            ast.Assign(targets=[ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
                                              attr=slot,
                                              ctx=ast.Store())],
                       value=ast.Name(id=slot, ctx=ast.Load()))
            for slot in dict_['__slots__']
        ]
        
        # We then compile and execute the AST in the local scope, and use the
        # result to create the class's __init__ method.
        ast.fix_missing_locations(f)
        exec(compile(ast.Module(body=[f]), '<string>', 'exec'))
        
        dict_['__init__'] = __init__
        
        # Note that we dynamically extend the class's MRO.
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
