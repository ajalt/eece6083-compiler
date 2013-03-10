'''Perform optimizations on an AST.

The optimizer assumes the AST is both syntactically and semanctically valid.'''

import itertools

import tokens
import syntaxtree

class ConstantFolder(syntaxtree.TreeMutator):
    '''Optimizer that performs constant folding within single expressions.'''
    def __init__(self):
        self.visit_functions = {
            syntaxtree.BinaryOp: self.visit_binary_op,
            syntaxtree.UnaryOp: self.visit_unary_op,
        }
        
        self.modified_tree = False
        
    def get_const(self, node):
        if isinstance(node, syntaxtree.Num):
            return node.n
        return None
    
    def is_literal(self, node):
        return isinstance(node, (syntaxtree.Num, syntaxtree.Str))
    
    def visit_binary_op(self, node):
        # Fold children first to allow for partial folding of an expression.
        self.visit_children(node)
        
        left = self.get_const(node.left)
        right = self.get_const(node.right)
        if left is not None and right is not None:
            self.modified_tree = True
            result = eval('%s %s %s' % (left, node.op, right))
            if result is True:
                return syntaxtree.Num('1')
            if result is False:
                return syntaxtree.Num('0')
            return syntaxtree.Num(str(result))
        return node
    
    def visit_unary_op(self, node):
        self.visit_children(node)
        
        operand = self.get_const(node.operand)
        if operand is not None:
            self.modified_tree = True
            return syntaxtree.Num(str(eval('%s %s' % (node.op, operand))))
        return node

class ConstantPropagator(ConstantFolder):
    '''Optimize that performs both constant folding and propagation.'''
    def __init__(self, print_errors=False):
        self.print_errors = print_errors
        
        # Scopes store the value of variables known to be constant, and the
        # declarations of procedures, so that we can tell which paratmters are in/out
        self.global_scope = {}
        self.scopes = [{}]
        
        self.visit_functions = {
            syntaxtree.Program: self.visit_program,
            syntaxtree.ProcDecl: self.visit_procdecl,
            syntaxtree.Assign: self.visit_assign,
            syntaxtree.BinaryOp: self.visit_binary_op,
            syntaxtree.UnaryOp: self.visit_unary_op,
            syntaxtree.If: self.visit_jump,
            syntaxtree.For: self.visit_jump,
            syntaxtree.Call: self.visit_call,
        }
        
        self.modified_tree = False
        
        # Use a stack to keep track of whether we're in a loop or not since we
        # can have nested loops.
        self.stop_propagation = []
        
    def enter_scope(self):
        self.scopes.append({})

    def leave_scope(self):
        self.scopes.pop()

    def define_variable(self, name, value, is_global=False):
        if is_global:
            self.global_scope[name] = value
        else:
            self.scopes[-1][name] = value

    def get_var(self, name):
        if isinstance(name, syntaxtree.Name):
            key = name
        elif isinstance(name, syntaxtree.Subscript):
            key = name.name
        
        try:
            return self.scopes[-1][key]
        except KeyError:
            try:
                return self.global_scope[key]
            except KeyError:
                # if we get here, it means an uninitialized variable was used.
                if self.print_errors:
                    msg = 'Uninitialzed variable referenced'
                    if name.token:
                        underline = '^' if name.token.start == name.token.end else '~'
                        line = name.token.line.rstrip()
                        print ('Error on line %s: %s\n'
                                '    %s\n'
                                '    %s') % (name.token.lineno, msg, line,
                                             ''.join((underline if name.token.start <= i <= name.token.end else ' ')
                                                        for i in xrange(len(line))))
                    else:
                        print msg
                
                self.print_errors = False
                return None
                
        
    def get_const(self, node):
        if isinstance(node, syntaxtree.Num):
            return node.n
        
        if isinstance(node, syntaxtree.Name):
            value = self.get_var(node)
            if isinstance(value, syntaxtree.Num):
                    return value.n
        return None
    
    def visit_program(self, node):
        for decl in node.decls:
            if isinstance(decl, syntaxtree.ProcDecl):
                self.define_variable(decl.name, decl, decl.is_global)
                
        self.visit_children(node)
        return node

    def visit_procdecl(self, node):
        self.enter_scope()
        
        for decl in node.decls:
            if isinstance(decl, syntaxtree.ProcDecl):
                self.define_variable(decl.name, decl)
            
        self.visit_children(node)
            
        self.leave_scope()
        
        return node
    
    def visit_assign(self, node):
        # self.visit_children will fold the value if possible
        self.visit_children(node)
        # Don't propagate arrays, since that could take up too much memory.
        if isinstance(node.target, syntaxtree.Name):
            if self.stop_propagation:
                # Unset any variables we find if we're in a loop or branch
                self.define_variable(node.target, None)
            elif self.is_literal(node.value):
                self.define_variable(node.target, node.value)

        return node
    
    def visit_jump(self, node):
        self.stop_propagation.append(True)
        self.visit_children(node)
        self.stop_propagation.pop()
        return node
    
    def visit_call(self, node):
        decl = self.get_var(node.func)
        for param, arg in itertools.izip(decl.params, node.args):
            # Unset variables sent as out parameters
            if param.direction == tokens.OUT:
                self.define_variable(arg, None)
        return node
    
class DeadCodeEliminator(syntaxtree.TreeMutator):
    def __init__(self):
        self.visit_functions = {
            syntaxtree.If: self.visit_if,
            syntaxtree.For: self.visit_for,
        }
        
        self.modified_tree = False
        
    def enter_scope(self):
        self.scopes.append({})

    def leave_scope(self):
        self.scopes.pop()

    def define_variable(self, name, value, is_global=False):
        if is_global:
            self.global_scope[name] = value
        else:
            self.scopes[-1][name] = value
            
    def visit_if(self, node):
        if node.test == syntaxtree.Num('1'):
            self.modified_tree = True
            return node.body
        if node.test == syntaxtree.Num('0'):
            # The orelse can be empty, which removes this node.
            self.modified_tree = True
            return node.orelse
        return node
    
    def visit_for(self, node):
        if node.test == syntaxtree.Num('0'):
            self.modified_tree = True
            return None
        return node
    
def optimize_tree(ast, level=1):
    if level == 0:
        return
    if level == 1:
        ConstantFolder().walk(ast)
    if level == 2:
        for i in xrange(3):
            propagator = ConstantPropagator(print_errors=(i == 0))
            propagator.walk(ast)
            if not propagator.modified_tree:
                return
            eliminator = DeadCodeEliminator()
            eliminator.walk(ast)
            if not eliminator.modified_tree:
                return
    
if __name__ == '__main__':
    import scanner
    import parser
    import typechecker
    
    src = '''
    program test_program is
    int a;
    int b;
    int c;
    int r;
    begin
        a := 15 + 15;
        b := 9 - a / (2 + 3);
        c :=  b * 4;
        if (c > 10) then
            c := c - 10;
        end if;
        r := c * (60 / a);
    end program
    '''
    
    #src = '''
    #program test_program is
    #int a;
    #int b;
    #procedure f(int x out, int y in)
    #begin end procedure;
    #begin
    #    a := 1;
    #    b := 2 + b;
    #    f(a,b);
    #    a := a + 1;
    #    b := b + 1;
    #end program
    #'''

    ast = parser.parse_tokens(scanner.tokenize_string(src))
    if typechecker.tree_is_valid(ast):
        optimize_tree(ast, 2)
        syntaxtree.dump_tree(ast)
    
