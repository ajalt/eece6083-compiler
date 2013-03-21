import sys

import syntaxtree
import tokens


class CodeGenerator(syntaxtree.TreeWalker):
    def __init__(self, output=sys.stdout):
        super(CodeGenerator, self).__init__()
        self.visit_functions = {
            syntaxtree.BinaryOp: self.visit_binop,
            syntaxtree.Num: self.visit_num,
            syntaxtree.Name: self.visit_name,
            syntaxtree.Str: self.visit_str,
            syntaxtree.UnaryOp: self.visit_unaryop,
        }
        
        self.output = output
        self.register_assignements = {}
        self.free_register = 0
        
    def write(self, text):
        print >> self.output, text
        
    def get_register(self, node):
        return 'TODO'
        
    def visit_num(self, node):
        return node.n
    
    def visit_str(self, node):
        return node.s
    
    def visit_name(self, node):
        return get_register(node)
    
    def visit_unaryop(self, node):
        value = self.visit(node.operand)
        print node
        if (isinstance(node.operand, syntaxtree.BinaryOp) or
            isinstance(node.operand, syntaxtree.UnaryOp)):
            self.free_register -= 1
        self.write('R[%s] = %s%s' % (self.free_register, node.op, value))
        self.free_register += 1
        return 'R[%s]' % (self.free_register - 1)
        
    def visit_binop(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        # Reuse temporary registers.
        for child in node.left, node.right:
            if (isinstance(child, syntaxtree.BinaryOp) or
                isinstance(child, syntaxtree.UnaryOp)):
                self.free_register -= 1
        
        self.write('R[%d] = %s %s %s' % (self.free_register, left, node.op, right))
        self.free_register += 1
        return 'R[%s]' % (self.free_register - 1)
        
        
if __name__ == '__main__':
    import scanner
    import parser
    import typechecker
    
    src = '''
    1 + -2
    '''
    
    ast = parser.Parser(scanner.tokenize_string(src)).expression()
    if typechecker.tree_is_valid(ast):
        CodeGenerator().walk(ast)
    
    
    
        
        
        
        
        