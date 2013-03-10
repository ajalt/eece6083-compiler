'''Perform optimizations on an AST.

The optimizer assumes the AST is both syntactically and semanctically valid.'''

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
    def __init__(self):
        self.global_scope = {}
        self.scopes = [{}]
        
        self.visit_functions = {
            syntaxtree.ProcDecl: self.visit_procdecl,
            syntaxtree.Assign: self.visit_assign,
            syntaxtree.BinaryOp: self.visit_binary_op,
            syntaxtree.UnaryOp: self.visit_unary_op,
            syntaxtree.If: self.visit_jump,
            syntaxtree.For: self.visit_jump,
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
            return self.global_scope[key]
        
    def get_const(self, node):
        if isinstance(node, syntaxtree.Num):
            return node.n
        
        if isinstance(node, syntaxtree.Name):
            value = self.get_var(node)
            if isinstance(value, syntaxtree.Num):
                    return value.n
        return None

    def visit_procdecl(self, node):
        self.enter_scope()
        
        # We have to add declarations to the scope here so that they properly
        # shadow global names
        
        ## Add parameters to scope.
        #for param in node.params:
        #    if param.direction == tokens.IN:
        #        self.define_variable(param.var_decl.name, None)
        # Add local variables to scope.
        for decl in node.decls:
            self.define_variable(decl.name, None)
            
        self.visit_children(node)
            
        self.leave_scope()
        
        return node
    
    def visit_assign(self, node):
        # self.visit_children will fold the value if possible
        self.visit_children(node)
        
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
    
class DeadCodeEliminator(syntaxtree.TreeMutator):
    def __init__(self):
        self.visit_functions = {
            syntaxtree.If: self.visit_if,
            syntaxtree.For: self.visit_for,
        }
        
        self.modified_tree = False
        
    def visit_if(self, node):
        print node
        if node.test == syntaxtree.Num('1'):
            return node.body
        if node.test == syntaxtree.Num('0'):
            return node.orelse
        return node
    
    def visit_for(self, node):
        if node.test == syntaxtree.Num('0'):
            return None
        return node
    
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

    ast = parser.parse_tokens(scanner.tokenize_string(src))
    if typechecker.tree_is_valid(ast):
        ConstantPropagator().walk(ast)
        DeadCodeEliminator().walk(ast)
        ConstantPropagator().walk(ast)
        
        syntaxtree.dump_tree(ast)
    
