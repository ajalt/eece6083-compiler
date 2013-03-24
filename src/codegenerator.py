import sys
import heapq
import collections

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
        
    def get(self):
        return heapq.heappop(self.queue)
    
class Register(int):
    def __str__(self):
        return 'R[%d]' % self
    
class RegisterHeap(Heap):
    def __init__(self):
        super(RegisterHeap, self).__init__([])
        self.size = 0
        self.max_size = 0
        
    def get(self):
        if self.queue:
            return super(RegisterHeap, self).get()
        self.size += 1
        self.max_size = max((self.size, self.max_size))
        return Register(self.size - 1)
    
    def clear(self):
        self.queue = []
        self.size = 0

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
            syntaxtree.Call: self.visit_call,
            syntaxtree.Subscript: self.visit_subscript,
        }
        
        self.output_file = output_file
        self.generate_comments = generate_comments
        self.register_assignements = {}
        self.free_registers = RegisterHeap()
        
        self.global_memory_locations = {}
        self.global_labels = {}
        self.fp_offsets = [{}]
        self.call_counts = collections.defaultdict(int)
        
    @staticmethod
    def allocates_register(node):
        '''Return whether or not a node allocates a register in its visit function.'''
        return (isinstance(node, syntaxtree.BinaryOp) or
                isinstance(node, syntaxtree.UnaryOp) or
                isinstance(node, syntaxtree.Subscript))
        
    @property
    def current_fp_offset(self):
        return self.fp_offsets[-1]
    
    def enter_scope(self, local_vars=(), params=()):
        self.fp_offsets.append({})

    def leave_scope(self):
        self.fp_offsets.pop()
        self.register_assignements = {}
        self.free_registers.clear()
        
    def write(self, text, indent='    '):
        print >> self.output_file, indent + text
        
    def get_memory_location(self, name):
        if name in self.global_memory_locations:
            return str(self.global_memory_locations[name])
        elif self.current_fp_offset[name] < 0:
            # Parameters are passed by reference
            return 'MM[FP%d]' % self.current_fp_offset[name]
        else:
            return 'FP + %d' % self.current_fp_offset[name]
        
    def get_register(self, node):
        try:
            return self.register_assignements[node]
        except KeyError:
            reg = self.free_registers.get()
            value = 'MM[%s]' % self.get_memory_location(node)
            if self.generate_comments:
                self.write('%s = %s; /* %s */' % (reg, value, node.id))
            else:
                self.write('%s = %s;' % (reg, value))

            self.register_assignements[node] = reg
            return reg
        
    def calc_sp_offset(self, node):
        sp_offset = 1
        for decl in node.decls:
            if isinstance(decl, syntaxtree.VarDecl):
                if decl.is_global:
                    # Since FP and SP both equal 0 at the start of the program,
                    # the offset is the static memory location.
                    self.global_memory_locations[decl.name] = sp_offset
                else:
                    self.current_fp_offset[decl.name] = sp_offset
                if decl.array_length:
                    sp_offset += int(decl.array_length.n)
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
            self.current_fp_offset[param.var_decl.name] = -i
        
        # Mangle global procedure names so that their definitions can be
        # shadowed by local declarations later.
        if node.is_global:
            label = '__global_%s' % node.name.id
            self.global_labels[node.name] = label
        else:
            label = node.name.id
        self.write('\n%s:' % label, indent='')
        
        # Add to the offsets to account for the return address and the previous
        # FP.
        self.write('FP = FP + %d;' % (len(node.params) + 2))
        self.write('SP = SP + %d;' % (len(node.params) + sp_offset + 1))
        
        for statement in node.body:
            self.visit(statement)
            
        if self.generate_comments:
            self.write('/* Unwind the stack. */')
            
        self.write('SP = FP - %d;' % (len(node.params) + 2))
        self.write('R[0] = MM[FP];')
        self.write('FP = MM[FP-1];')
        self.write('goto *(void *)R[0];')
        
        self.leave_scope()
        
    def visit_program(self, node):
        self.write('#define true 1', indent='')
        self.write('#define false 0\n', indent='')
        self.write('extern int R[];', indent='')
        self.write('int MM[1000];', indent='')
        self.write('int SP = 0;', indent='')
        self.write('int FP = 0;', indent='')
        self.write('\nint main() {', indent='')
        self.write('goto %s;' % node.name.id)

        # Subtract 1 from the offset, since we don't have a previous FP to
        # account for.
        sp_offset = self.calc_sp_offset(node) - 1
        
        self.write('\n%s:' % node.name.id, indent='')

        if sp_offset > 0:
            self.write('SP = SP + %d;' % sp_offset )
        
        for statement in node.body:
            self.visit(statement)
            
        # The main function will be the last one generated. It can't return a
        # value, so we don't have to unwind the stack.
        self.write('return 0;')
        self.write('}\n', indent='')
        
        # Define the register size here now that we know how big it will get.
        self.write('int R[%d];' % (self.free_registers.max_size), indent='')

    def visit_num(self, node):
        return node.n
    
    def visit_str(self, node):
        return '(int) %s' % node.s
    
    def visit_name(self, node):
        return self.get_register(node)
    
    def visit_subscript(self, node):
        base = self.get_memory_location(node.name)
        offset = self.visit(node.index)
        reg = self.free_registers.get()
        if self.generate_comments:
            line = node.name.token.line
            endpos = line.find(']', node.name.token.end)
            if endpos > 0:
                comment = line[node.name.token.start:endpos + 1]
            else:
                comment = '%s[...]' % node.name.id
            
            self.write('R[%d] = %s; /* %s */' % (reg, base, comment))
        else:
            self.write('R[%d] = %s;' % (reg, base))
        self.write('R[%d] = R[%d] + %s' % (reg, reg, offset))
        self.write('R[%d] = MM[R[%d]];' % (reg, reg))
        return reg
    
    def visit_unaryop(self, node):
        value = self.visit(node.operand)
        
        if self.allocates_register(node.operand):
            self.free_registers.put(value)
            
        outreg = self.free_registers.get()
        
        # Trnaslate the not operator into the C equivalent, which is dependant
        # on the data type.
        op = node.op
        if op == tokens.NOT:
            if node.node_type == tokens.BOOL:
                op = '!'
                self.write("validateBooleanOp(%s, '%s', %s, %d);" %
                           (0, op, value, node.token.lineno))
            else:
                op = '~'
                
        self.write('%s = %s%s;' % (outreg, op, value))
        return outreg
        
    def visit_binop(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        # Free temporary registers.
        if self.allocates_register(node.right):
            self.free_registers.put(right)
        if self.allocates_register(node.left):
            self.free_registers.put(left)
        
        outreg = self.free_registers.get()
        
        if node.node_type == tokens.BOOL:
            self.write("validateBooleanOp(%s, '%s', %s, %s);" %
                       (left, node.op, right, node.token.lineno))
        self.write('%s = %s %s %s;' % (outreg, left, node.op, right))
        return outreg
    
    def visit_assign(self, node):
        if node.token:
            t = node.token
            if self.generate_comments:
                self.write('/* %s */' % t.line[t.start:t.end+1])
            
        value = self.visit(node.value)
        outreg = self.visit(node.target)
        
        if self.allocates_register(node.value):
            self.free_registers.put(value)
        
        self.write('%s = %s;' % (outreg, value))
        
    def visit_call(self, node):
        call_label = self.global_labels.get(node.func, node.func)
        return_label = 'return_from_%s_%s' % (call_label,
                                              self.call_counts[call_label])
        self.call_counts[call_label] += 1
        
        # Push the refrerences to the arguments right-to-left
        for i, arg in enumerate(reversed(node.args)):
            self.write('MM[SP+%d] = %s;' % (i + 1, self.get_memory_location(arg)))
        self.write('MM[SP+%d] = FP;' % (i+2))
        self.write('MM[SP+%d] (int)&&%s;' % (i+3, return_label))
        self.write('goto %s;' % call_label)
        self.write('%s:' % return_label, indent='')
            
    
        
if __name__ == '__main__':
    import scanner
    import parser
    import typechecker
    
    #src = '''
    #program test_program is
    #    int i[5];
    #    procedure proc (int j[5] in)
    #        int k;
    #    begin
    #        k := j[20];
    #    end procedure;
    #begin
    #    i[0] := 10;
    #end program;
    #'''
    
    src = '''
    program test_program is
        int a[5];
        procedure proc (int j in)
            int k;
        begin
            k := j;
        end procedure;
    begin
        a[3] := 123;
    end program;
    '''
    
    ast = parser.parse_tokens(scanner.tokenize_string(src))
    if typechecker.tree_is_valid(ast):
        CodeGenerator(generate_comments=True).walk(ast)
    
    
    
        
        
        
        
        