import sys
import heapq

import syntaxtree
import tokens

# The calling convention follows the __stdcall format: the callee unwinds the
# stack, and arguments are pushed right-to-left.The stack grows up in the memory
# space.
# The format of the stack is:
#
# --------------------- 
#    Local variables    <- SP
#    .
#    .
#    .
# ---------------------
#    Return address     <- FP
# ---------------------
#    Caller FP
# ---------------------
#    Parameters
#    .
#    .
#    .
# ---------------------
# 

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
        self.max_size = 0
        
    def pop(self):
        if self.queue:
            return super(RegisterHeap, self).pop()
        self.size += 1
        self.max_size = max((self.size, self.max_size))
        return Register(self.size - 1)
    
    def clear(self):
        self.queue = []
        self.size = 0

def is_op(node):
    return (isinstance(node, syntaxtree.BinaryOp) or
            isinstance(node, syntaxtree.UnaryOp))

class CodeGenerator(syntaxtree.TreeWalker):
    def __init__(self, output_file=sys.stdout, generate_comments=False):
        super(CodeGenerator, self).__init__()
        self.visit_functions = {
            syntaxtree.BinaryOp: self.visit_binop,
            syntaxtree.Num: self.visit_num,
            syntaxtree.Name: self.visit_name,
            syntaxtree.Str: self.visit_str,
            syntaxtree.UnaryOp: self.visit_unaryop,
            syntaxtree.Assign: self.visit_assign,
            syntaxtree.ProcDecl: self.visit_procdecl,
            syntaxtree.Program: self.visit_program,
        }
        
        self.output_file = output_file
        self.generate_comments = generate_comments
        self.register_assignements = {}
        self.free_registers = RegisterHeap()
        
        # Scopes store a map of names to memory locations
        self.global_scope = {}
        self.scopes = [{}]
        
    @property
    def current_scope(self):
        return self.scopes[-1]
        
    def enter_scope(self, local_vars=(), params=()):
        self.scopes.append({})

    def leave_scope(self):
        self.scopes.pop()
        self.register_assignements = {}
        self.free_registers.clear()
        
    def write(self, text, indent='    '):
        print >> self.output_file, indent + text
        
    def get_memory_location(self, name):
        pass
        
    def get_register(self, node):
        try:
            return self.register_assignements[node]
        except KeyError:
            reg = self.free_registers.pop()
            if node in self.global_scope:
                location = 'MM[%d]' % self.global_scope[node]
            elif self.current_scope[node] < 0:
                location = 'MM[FP%d]' % self.current_scope[node]
            else:
                location = 'MM[FP+%d]' % self.current_scope[node]
            if self.generate_comments:
                self.write('%s = %s /* %s */' % (reg, location, node.id))
            else:
                self.write('%s = %s' % (reg, location))

            self.register_assignements[node] = reg
            return reg
        
    def calc_sp_offset(self, node):
        sp_offset = 1
        for decl in node.decls:
            if isinstance(decl, syntaxtree.VarDecl):
                if decl.is_global:
                    # Since FP and SP both equal 0 at the start of the program,
                    # the offset is the static memory location.
                    self.global_scope[decl.name] = sp_offset
                else:
                    self.current_scope[decl.name] = sp_offset
                if decl.array_length:
                    sp_offset += decl.array_length
                else:
                    sp_offset += 1
            else:
                # Define children first so that we don't have to split up
                # procedure definitions.
                self.visit(decl)
        return sp_offset
        
    def visit_procdecl(self, node):
        self.enter_scope()
        
        sp_offset = self.calc_sp_offset(node)
        
        for i, param in enumerate(node.params, 2):
            self.current_scope[param.var_decl.name] = -i
        
        # Mangle global procedure names so that their definitions can be
        # shadowed by local declarations later.
        if node.is_global:
            label = '__global_%s' % node.name.id
        else:
            label = node.name.id
        self.write('\n%s:' % label, indent='')
        
        # Add to the offsets to account for the return address and the previous
        # FP.
        self.write('FP = FP + %d' % (len(node.params) + 2))
        self.write('SP = SP + %d' % (len(node.params) + sp_offset + 1))
        
        for statement in node.body:
            self.visit(statement)
            
        if self.generate_comments:
            self.write('/* Unwind the stack. */')
            
        self.write('SP = FP - %d' % (len(node.params) + 2))
        self.write('R[0] = MM[FP]')
        self.write('FP = MM[FP-1]')
        self.write('goto *(void *)R[0]')
        
        self.leave_scope()
        
    def visit_program(self, node):
        self.write('extern int R[];', indent='')
        self.write('int MM[1000];', indent='')
        self.write('int SP = 0;', indent='')
        self.write('int FP = 0;', indent='')
        self.write('int main() {', indent='')
        self.write('goto %s;' % node.name.id)

        # Subtract 1 from the offset, since we don't have a previous FP to
        # account for.
        sp_offset = self.calc_sp_offset(node) - 1
        
        self.write('\n%s:' % node.name.id, indent='')

        if sp_offset > 0:
            self.write('SP = SP + %d' % sp_offset )
        
        for statement in node.body:
            self.visit(statement)
            
        # The main function will be the last one generated. It can't return a
        # value, so we don't have to unwind the stack.
        self.write('return 0;')
        self.write('}\n', indent='')
        
        # Define the register size here now that we know how big it will get.
        self.write('int R[%d];' % (self.free_registers.max_size + 1), indent='')

    def visit_num(self, node):
        return node.n
    
    def visit_str(self, node):
        return '(int) %s' % node.s
    
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
            if self.generate_comments:
                self.write('/* %s */' % t.line[t.start:t.end+1])
            
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
    program test_program is
        global int i;
        procedure proc (int j in)
            int k;
        begin
            k := i;
            k := k + i + j;
        end procedure;
    begin
        i := 20;
    end program;
    '''
    
    ast = parser.parse_tokens(scanner.tokenize_string(src))
    if typechecker.tree_is_valid(ast):
        CodeGenerator(generate_comments=True).walk(ast)
    
    
    
        
        
        
        
        