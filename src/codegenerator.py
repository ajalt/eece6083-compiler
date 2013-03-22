import sys
import heapq

import syntaxtree
import tokens

R_SIZE = 255

class Heap(object):
    def __init__(self, items):
        self.queue = items
        heapq.heapify(self.queue)
        
    def put(self, item):
        heapq.heappush(self.queue, item)
        
    def pop(self):
        return heapq.heappop(self.queue)
    
class Register(int):
    def __str__(self):
        return 'R[%d]' % self
    
class RegisterHeap(Heap):
    def __init__(self):
        super(RegisterHeap, self).__init__([])
        self.size = 0
        
    def pop(self):
        if self.queue:
            return super(RegisterHeap, self).pop()
        self.size += 1
        if self.size > R_SIZE:
            raise IndexError('RegisterHeap out of available registers')
        return Register(self.size - 1)

def is_op(node):
    return (isinstance(node, syntaxtree.BinaryOp) or
            isinstance(node, syntaxtree.UnaryOp))

class CodeGenerator(syntaxtree.TreeWalker):
    def __init__(self, output=sys.stdout):
        super(CodeGenerator, self).__init__()
        self.visit_functions = {
            syntaxtree.BinaryOp: self.visit_binop,
            syntaxtree.Num: self.visit_num,
            syntaxtree.Name: self.visit_name,
            syntaxtree.Str: self.visit_str,
            syntaxtree.UnaryOp: self.visit_unaryop,
            syntaxtree.Assign: self.visit_assign,
        }
        
        self.output = output
        self.register_assignements = {}
        self.free_registers = RegisterHeap()
        
    def write(self, text):
        print >> self.output, text
        
    def get_register(self, node):
        try:
            return self.register_assignements[node]
        except KeyError:
            reg = self.free_registers.pop()
            self.write('%s = %s' % (reg, node.id))
            self.register_assignements[node] = reg
            return reg
        
    def visit_num(self, node):
        return node.n
    
    def visit_str(self, node):
        return node.s
    
    def visit_name(self, node):
        return self.get_register(node)
    
    def visit_unaryop(self, node):
        value = self.visit(node.operand)
        
        if is_op(node.operand):
            self.free_registers.put(value)
            
        outreg = self.free_registers.pop()
        self.write('%s = %s%s' % (outreg, node.op, value))
        return outreg
        
    def visit_binop(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        # Free temporary registers.
        if is_op(node.right):
            self.free_registers.put(right)
        if is_op(node.left):
            self.free_registers.put(left)
        
        outreg = self.free_registers.pop()
        
        self.write('%s = %s %s %s' % (outreg, left, node.op, right))
        return outreg
    
    def visit_assign(self, node):
        if node.token:
            t = node.token
            self.write('// %s' % t.line[t.start:t.end+1])
            
        value = self.visit(node.value)
        outreg = self.visit(node.target)
        
        if is_op(node.value):
            self.free_registers.put(value)
        
        self.write('%s = %s' % (outreg, value))
            
        
        
if __name__ == '__main__':
    import scanner
    import parser
    import typechecker
    
    src = '''
    x := -a + -b + (-c * -a - 10);
    '''
    
    ast = parser.Parser(scanner.tokenize_string(src)).statement()
    #if typechecker.tree_is_valid(ast):
    CodeGenerator().walk(ast)
    
    
    
        
        
        
        
        