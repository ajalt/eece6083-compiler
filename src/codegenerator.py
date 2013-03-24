import sys
import heapq
import collections

import syntaxtree
import tokens

# The code generator generates code using four types of memory addressing:
# Absolute, Register, Register Offset, and Memory Indirect.
#
# The calling convention follows the __stdcall format: the callee unwinds the
# stack, and arguments are pushed right-to-left.The stack grows up in the memory
# space. The format of the stack is:
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
            syntaxtree.ProcDecl: self.visit_procdecl,
            syntaxtree.Assign: self.visit_assign,
            syntaxtree.If: self.visit_if,
            syntaxtree.For: self.visit_for,
            syntaxtree.BinaryOp: self.visit_binop,
            syntaxtree.Num: self.visit_num,
            syntaxtree.Name: self.visit_name,
            syntaxtree.Str: self.visit_str,
            syntaxtree.UnaryOp: self.visit_unaryop,
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
        self.label_counts = collections.defaultdict(int)
        self.last_subscript_address = None
        
    @staticmethod
    def allocated_register(node):
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
        
    def create_label(self, title):
        label = '%s_%d' % (title, self.label_counts[title])
        self.label_counts[title] += 1
        return label
        
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
    
    def store_variables(self, names):
        for name in names:
            reg = self.get_register(name)
            location = self.get_memory_location(name)
            if self.generate_comments:
                comment = ' /* store %s */' % name.id
            else:
                comment = ''
            self.write('MM[%s] = %s;%s' % (location, reg, comment))
        
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
            
        outparams = (p.var_decl.name for p in node.params if p.direction == tokens.OUT)
        self.store_variables(outparams)
            
        if self.generate_comments:
            self.write('/* Unwind the stack. */')
            
        self.write('SP = FP - %d;' % (len(node.params) + 2))
        self.write('R[0] = MM[FP];')
        self.write('FP = MM[FP-1];')
        self.write('goto *(void *)R[0];')
        
        self.leave_scope()
        
    def visit_program(self, node):
        self.write('#include "string.h"', indent='')
        self.write('#define true 1', indent='')
        self.write('#define false 0', indent='')
        self.write('#define MM_SIZE 32768\n', indent='') # 32K
        self.write('extern int R[];', indent='')
        self.write('int MM[MM_SIZE];', indent='')
        self.write('float FLOAT_REG_1;', indent='') 
        self.write('float FLOAT_REG_2;', indent='')
        self.write('int SP = 0;', indent='') # stack pointer
        self.write('int FP = 0;', indent='') # frame pointer
        self.write('int HP = MM_SIZE - 1;', indent='') # heap pointer
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
        address_reg = self.free_registers.get()
        value_reg = self.free_registers.get()
        
        if self.generate_comments:
            line = node.name.token.line
            endpos = line.find(']', node.name.token.end)
            if endpos > 0:
                comment = ' /* %s */' % line[node.name.token.start:endpos + 1]
            else:
                comment = ' /* %s[...] */' % node.name.id
            
        self.write('R[%d] = %s;%s' % (address_reg, base, comment))
        if offset > 0:
            self.write('R[%d] = R[%d] + %s;' % (address_reg, address_reg, offset))
        self.last_subscript_address = address_reg
        self.write('R[%d] = MM[R[%d]];' % (value_reg, address_reg))
        return value_reg
    
    def visit_unaryop(self, node):
        value = self.visit(node.operand)
        
        if self.allocated_register(node.operand):
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
        if self.allocated_register(node.right):
            self.free_registers.put(right)
        if self.allocated_register(node.left):
            self.free_registers.put(left)
        
        outreg = self.free_registers.get()
        
        if node.node_type == tokens.FLOAT:
            if isinstance(node.left, syntaxtree.Num):
                self.write('FLOAT_REG_1 = %s;' % left)
            else:
                self.write('memcpy(&FLOAT_REG_1, &%s, sizeof(float));' % left)
            if isinstance(node.right, syntaxtree.Num):
                self.write('FLOAT_REG_2 = %s;' % right)
            else:
                self.write('memcpy(&FLOAT_REG_2, &%s, sizeof(float));' % right)
            self.write('FLOAT_REG_1 = FLOAT_REG_1 %s FLOAT_REG_2;' % node.op)
            self.write('memcpy(&%s, &FLOAT_REG_1, sizeof(float));' % outreg)
        else:    
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
        if isinstance(node.value, syntaxtree.Num) and '.' in node.value.n:
            self.write('FLOAT_REG_1 = %s;' % value)
            self.write('memcpy(&%s, &FLOAT_REG_1, sizeof(float));' % outreg)
        else:
            self.write('%s = %s;' % (outreg, value))
        
        # Store array assignments immediatly to save registers
        if isinstance(node.target, syntaxtree.Subscript):
            self.write('MM[%s] = %s;' % (self.last_subscript_address, outreg))
            self.free_registers.put(self.last_subscript_address)
        
        if self.allocated_register(node.value):
            self.free_registers.put(value)
        
    def visit_call(self, node):
        call_label = self.global_labels.get(node.func, node.func.id)
        return_label = self.create_label('return_from_%s' % call_label)
        
        if self.generate_comments:
            line = node.func.token.line
            startpos = node.func.token.start
            endpos = line.index(';', startpos)
            self.write('/* %s */' % line[startpos:endpos])
        
        self.store_variables(self.register_assignements)
        
        self.write('MM[SP + 1] = FP;')
        self.write('MM[SP + 2] = (int)&&%s;' % return_label)
        
        # Push the refrerences to the arguments right-to-left
        reg = self.free_registers.get()
        for i, arg in enumerate(reversed(node.args)):
            self.write('%s = %s;' % (reg, self.get_memory_location(arg)))
            self.write('MM[SP + %d] = %s;' % (i + 3, reg))
        
        self.write('goto %s;' % call_label)
        self.write('\n%s:' % return_label, indent='')
            
        self.register_assignements.clear()
        
    def visit_if(self, node):
        test_reg = self.visit(node.test)
        endif_label = self.create_label('__endif')
        
        if node.orelse:
            target_label = self.create_label('__else')
        
        self.write('if (!%s) goto %s;' % (test_reg, target_label)) 
        for statement in node.body:
            self.visit(statement)
            
        if node.orelse:
            self.write('goto %s;' % endif_label)
            self.write('\n%s:' % target_label, indent='')
            for statement in node.orelse:
                self.visit(statement)
            
        self.write('\n%s:' % endif_label, indent='')
        
    def visit_for(self, node):
        self.visit(node.assignment)
        start_label = self.create_label('__for')
        end_label = self.create_label('__endfor')
        
        self.write('\n%s:' % start_label)
        # XXX: Putting the test blindly inside the label will cause the program
        # to load the variable from memory at the start of the loop, with
        # results in an infinite loop if the test variable is unreferenced
        # before the loop. Programs testing uninitialized variables are
        # illformed anyway. A workaround would be to load all variables at the
        # start of a function.
        test_reg = self.visit(node.test)
        self.write('if (!%s) goto %s;' % (test_reg, end_label))
        
        for statement in node.body:
            self.visit(statement)
            
        self.write('\n%s:' % end_label)
        
if __name__ == '__main__':
    import scanner
    import parser
    import typechecker
    
    src = '''
    program test_program is
        float a;
        float b;
        //procedure proc (int j[6] in, int h out)
        //    int k;
        //begin
        //    proc(j, h);
        //end procedure;
    begin
        a := 11.0 + 12.0;
        b := 22.0;
        a := a + b;
    end program;
    '''
    
    ast = parser.parse_tokens(scanner.tokenize_string(src))
    if typechecker.tree_is_valid(ast):
        CodeGenerator(generate_comments=True).walk(ast)
    
    
    
        
        
        
        
        