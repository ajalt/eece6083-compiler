'''Perform optimizations on an AST.

The optimizer assumes the AST is both syntactically and semanctically valid.'''

import tokens
import syntaxtree

class ConstantFolder(syntaxtree.TreeMutator):
    def __init__(self):
        self.global_scope = {}
        self.scopes = [{}]
        
        self.visit_functions = {
            syntaxtree.Program: self.visit_program,
            syntaxtree.ProcDecl: self.visit_procdecl,
            syntaxtree.Assign: self.visit_assign,
            syntaxtree.BinaryOp: self.visit_op,
            syntaxtree.UnaryOp: self.visit_op,
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
        
        value = None
        if isinstance(node, syntaxtree.BinaryOp):
            value = self.fold_binary_op(node)
        if isinstance(node, syntaxtree.UnaryOp):
            value =  self.fold_unary_op(node)
        if isinstance(node, syntaxtree.Name):
            value = self.get_var(node)
            
        if isinstance(value, syntaxtree.Num):
                return value.n
        return None
    
    def is_const(self, node):
        return isinstance(node, (syntaxtree.Num, syntaxtree.Str))
    
    def fold_binary_op(self, node):
        left = self.get_const(node.left)
        if left is not None:
            right = self.get_const(node.right)
            if right is not None:
                print (left, node.op, right)
                result = eval('%s %s %s' % (left, node.op, right))
                if result is True:
                    return syntaxtree.Num('1')
                if result is False:
                    return syntaxtree.Num('0')
                return syntaxtree.Num(str(result))
        return None
    
    def fold_unary_op(self, node):
        operand = self.get_const(node.operand)
        if operand is not None:
            return syntaxtree.Num(str(eval('%s %s' % (node.op, operand))))
        return None
    
    def visit_program(self, node):
        for decl in node.decls:
            self.define_variable(decl.name, None, decl.is_global)
            
        self.visit_children(node)
        
        return node
        
    def visit_procdecl(self, node):
        self.enter_scope()
        
        # We have to add declarations to the scope here so that they properly
        # shadow global names
        
        # Add parameters to scope.
        for param in node.params:
            if param.direction == tokens.IN:
                self.define_variable(param.var_decl.name, None)
        # Add local variables to scope.
        for decl in node.decls:
            self.define_variable(decl.name, None)
            
        self.visit_children(node)
            
        self.leave_scope()
        
        return node
    
    def visit_assign(self, node):
        # self.visit_children will fold the value if possible
        self.visit_children(node)
        print node
        if self.is_const(node.value):
            self.define_variable(node.target, node.value)
        return node

    def visit_op(self, node):
        const = self.get_const(node)
        if const is not None:
            self.modified_tree = True
            return syntaxtree.Num(const)
        return node
    
    
if __name__ == '__main__':
    import scanner
    import parser
    import typechecker
    
    argparser = argparse.ArgumentParser(description='Test the type checking functionality.')
    
    argparser.add_argument('filename', help='the file to parse')
    args = argparser.parse_args()
    
    ast = parser.parse_tokens(scanner.tokenize_file(args.filename))
    if typechecker.tree_is_valid(ast):
        cf = ConstantFolder()
        cf.walk(ast)
        syntaxtree.dump_tree(ast)
    
