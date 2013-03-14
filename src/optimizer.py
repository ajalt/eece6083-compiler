'''Perform optimizations on an AST.

The optimize_tree function is the main interface to the optimizer, which will
optimize an AST in place. The function can optimize at two different levels.

Level 1: Minimal optimization is performed. The resulting tree is guaranteed to
be quivalent to the original.

Level 2: More extensive optimization is performed that may produce incorrect code.

The optimizer assumes the AST is both syntactically and semantically valid.'''

import itertools

import tokens
import syntaxtree

class ConstantFolder(syntaxtree.TreeMutator):
    '''Optimizer that performs constant folding within single expressions.'''
    def __init__(self):
        super(ConstantFolder, self).__init__()
        
        self.visit_functions = {
            syntaxtree.BinaryOp: self.visit_binary_op,
            syntaxtree.UnaryOp: self.visit_unary_op,
        }
        
    def get_const(self, node):
        '''Return the value of a constant AST node, or None if the node is not a number.'''
        if isinstance(node, syntaxtree.Num):
            return node.n
        return None
    
    def is_literal(self, node):
        return isinstance(node, (syntaxtree.Num, syntaxtree.Str))
    
    def visit_binary_op(self, node):
        # Fold children first so that we can fold parts of an expression even if
        # the entire expression is not constant.
        self.visit_children(node)
        
        left = self.get_const(node.left)
        if left is not None:
            right = self.get_const(node.right)
            if right is not None:
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
            return syntaxtree.Num(str(eval('%s %s' % (node.op, operand))))
        return node

class ConstantPropagator(ConstantFolder):
    '''Optimize that performs both constant folding and propagation.
    
    This optimizer can detect some uses of uninitialized variables and will
    optionally report them as errors.
    
    This optimizer combines constant folding and propagation into a single pass
    over the tree. By combining the two operations, we can save several walks
    over the tree that would be necessary if the two were interleaved.
    
    Instead of taking the time to construct explicit U-D chains for the
    propagation, we can simply record the constant value of known variables in a
    symbol table and invalidate that value if we reach a non-constant
    assignment. Since we do the propagation inline with folding, and the walk is
    in program order, this will produce correct code as long as we don't miss
    any invalidations.'''
    def __init__(self, print_errors=False):
        super(ConstantFolder, self).__init__()
        
        self.print_errors = print_errors
        
        # Scopes store the value of variables known to be constant, and the
        # declarations of procedures, so that we can tell which parameters are in/out
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
        
        # Use a stack to keep track of whether we're in a loop or not since we
        # can have nested blocks. If there is a value on this stack, all
        # assignments will result in an invalidation. This is more conservative
        # than necessary, but without more reaching definition analysis, we
        # can't tell if an assignment is loop-invariant.
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
                if self.print_errors:
                    msg = 'Uninitialized variable referenced'
                    if name.token:
                        underline = '^' if name.token.start == name.token.end else '~'
                        line = name.token.line.rstrip()
                        print ('Warning on line %s: %s\n'
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
        
        # Add this declaration to its own scope to allow recursion.
        self.define_variable(node.name, node)
        
        # Add parameters to so they don't get flagged as uninitialized reference errors.
        for param in node.params:
            self.define_variable(param.var_decl.name, None)
            
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
    '''Optimizer that elimiates dead branches, loops, assignemnts, and declarations.
    
    This optimizer does not construct explicit D-U chains or SSA structures.
    Instead, it works by walking the AST in reverse program order, which is a
    top-down, right-to-left walk of the AST, marking variables as used or
    assigned as it encounters them. When it reaches an assignment or
    declaration, it will have encountered all references to that identifier
    already.
    '''
    ASSIGNED = 1
    REFERENCED = 2
    
    def __init__(self):
        super(DeadCodeEliminator, self).__init__()
        
        # Scopes store whether variables have been read or assigned to
        # For procedures, they store a tuple of (decl, read or assigned)
        self.global_scope = {}
        self.scopes = []
        
        self.visit_functions = {
            syntaxtree.ProcDecl: self.visit_block,
            syntaxtree.Program: self.visit_block,
            syntaxtree.Assign: self.visit_assign,
            syntaxtree.Name: self.visit_name,
            syntaxtree.Call: self.visit_call,
            syntaxtree.If: self.visit_if,
            syntaxtree.For: self.visit_for,
            syntaxtree.VarDecl: self.visit_vardecl,
        }
        
        
    def enter_scope(self):
        self.scopes.append({})

    def leave_scope(self):
        self.scopes.pop()

    def define_var(self, name, value, is_global=False):
        if is_global:
            self.global_scope[name] = value
        else:
            self.scopes[-1][name] = value
            
    def set_var(self, name, value):
        if name in self.scopes[-1]:
            self.scopes[-1] = value
        elif name in self.global_scope:
            self.global_scope[name] = value
        # It's ok if we try to set undefined variables: we never define
        # procedure parameters since they can't be eliminated.
            
    def get_var(self, name):
        if isinstance(name, syntaxtree.Name):
            key = name
        elif isinstance(name, syntaxtree.Subscript):
            key = name.name
        
        try:
            return self.scopes[-1][key]
        except KeyError:
            return self.global_scope.get(key)
        
    def walk_body(self, node, attrname='body'):
        # Manually walk the body in reverse to construct implicit D-U Chains.
        new_body = []
        for child in reversed(getattr(node, attrname)):
            value = self._visit(child)
            if value is not None:
                if isinstance(value, list):
                    new_body = value + new_body
                else:
                    new_body.insert(0, value)
        setattr(node, attrname, new_body)
        
            
    def visit_block(self, node):
        # This function is used for both Program and ProcDecl nodes
        
        if isinstance(node, syntaxtree.ProcDecl):
            if self.get_var(node.name)[1]  is None:
                return None
        
        self.enter_scope()
        
        if isinstance(node, syntaxtree.ProcDecl):
            self.define_var(node.name, (node, None))
            
        for decl in node.decls:
            if isinstance(decl, syntaxtree.ProcDecl):
                self.define_var(decl.name, (decl, None), decl.is_global)
            else:
                self.define_var(decl.name, None)
        
        self.walk_body(node)
        self.walk_body(node, 'decls')
        
        # If there's a return in the body, it's isn't in a branch, so it always
        # terminates the procedure.
        try:
            del node.body[node.body.index(tokens.RETURN):]
        except ValueError:
            pass

        self.leave_scope()
    
        return node
    
    def visit_vardecl(self, node):
        if self.get_var(node.name) is None:
            return None
        return node
    
    def visit_assign(self, node):
        if self.get_var(node.target) == self.REFERENCED:
            self.define_var(node.target, self.ASSIGNED)
            return node
        return None

    def visit_name(self, node):
        self.define_var(node, self.REFERENCED)
        return node
        
    def visit_call(self, node):
        decl = self.get_var(node.func)[0]
        self.define_var(node.func, (decl, self.REFERENCED))
        for arg, param in itertools.izip(node.args, decl.params):
            if isinstance(arg, syntaxtree.Name):
                self.define_var(arg, self.REFERENCED if param.direction ==
                                            tokens.IN else self.ASSIGNED)
                
        return node
        
    def visit_if(self, node):
        if node.test == syntaxtree.Num('1'):
            self.walk_body(node)
            return node.body
        if node.test == syntaxtree.Num('0'):
            self.walk_body(node, 'orelse')
            # The orelse can be empty, which removes this node.
            return node.orelse
        if not node.body and not node.orelse:
            # In the only recorded case of the lack of functions being helpful,
            # expressions can't have side effects, which means we can drop the
            # test without worrying about what it's doing.
            return None
        self.walk_body(node, 'orelse')
        self.walk_body(node)
        self._visit(node.test)
        
        return node
    
    def visit_for(self, node):
        if node.test == syntaxtree.Num('0'):
            return None
        self._visit(node.test)
        self.walk_body(node)
        return node
    
def optimize_tree(ast, level=1):
    if level == 0:
        return
    if level == 1:
        ConstantFolder().walk(ast)
    if level == 2:
        ConstantPropagator(print_errors=True).walk(ast)
        DeadCodeEliminator().walk(ast)
        for i in xrange(3):
            propagator = ConstantPropagator()
            propagator.walk(ast)
            eliminator = DeadCodeEliminator()
            eliminator.walk(ast)
            if not propagator.modified_tree or not eliminator.modified_tree:
                return
    
if __name__ == '__main__':
    import argparse
    import scanner
    import parser
    import typechecker

    argparser = argparse.ArgumentParser(description='Test the type optimization functionality.')
    
    argparser.add_argument('filename', help='the file to parse')
    argparser.add_argument('-O', type=int, choices=[0, 1, 2], default=2,
                           help='the level of optimizaion to apply to the program (default 2)')
    args = argparser.parse_args()
    ast = parser.parse_tokens(scanner.tokenize_file(args.filename))
    if typechecker.tree_is_valid(ast):
        optimize_tree(ast, args.O)
        syntaxtree.dump_tree(ast)

    
