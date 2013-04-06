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

PROLOG = '''
#include "string.h"
#define true 1
#define false 0
#define MM_SIZE 32768
#define INPUT_BUFFER_SIZE 1024

extern int R[];
int MM[MM_SIZE];
char INPUT_BUFFER[INPUT_BUFFER_SIZE];
float FLOAT_REG_1; 
float FLOAT_REG_2;
int SP = 0; /* stack pointer */
int FP = 0; /* frame pointer */
int HP = MM_SIZE - 1; /* heap pointer */

int main() {
'''.strip()

runtime_functions = {
'getBool':'''
    R[0] = getBool();
    MM[MM[SP + 1]] = R[0]; 
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip(),
'getInteger':'''
    R[0] = getInteger();
    MM[MM[SP + 1]] = R[0]; 
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip(),
'getFloat':'''
    FLOAT_REG_1 = getFloat();
    memcpy(&R[0], &FLOAT_REG_1, sizeof(float));
    MM[MM[SP + 1]] = R[0]; 
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip(),
'getString':'''
    R[0] = getString(INPUT_BUFFER);
    HP = HP - R[0];
    memcpy(&MM[HP], &INPUT_BUFFER, R[0]);
    MM[MM[SP + 1]] = (int)((char *)&MM[HP]); 
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip(),
'putBool':'''
    R[0] = MM[SP + 1];
    putBool(R[0]);
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip(),
'putInteger':'''
    R[0] = MM[SP + 1];
    putInteger(R[0]);
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip(),
'putFloat':'''
    memcpy(&FLOAT_REG_1, &MM[SP + 1], sizeof(float));
    putFloat(FLOAT_REG_1);
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip(),
'putString':'''
    R[0] = MM[SP + 1];
    putString((char *)R[0]);
    R[0] = MM[SP + 3];
    goto *(void *)R[0];
'''.strip()
}

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
        self.fp_offsets = [{}]
        self.proc_decls = [{}]
        self.global_proc_decls = {}
        self.current_procedure = None
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
    
    def set_proc_decl(self, name, decl):
        if decl.is_global:
            self.global_proc_decls[name] = decl
        else:
            self.proc_decls[-1][name] = decl
            
    def get_proc_decl(self, name):
        if name in self.global_proc_decls:
            return self.global_proc_decls[name]
        else:
            return self.proc_decls[-1][name]
    
    def enter_scope(self):
        self.fp_offsets.append({})
        self.proc_decls.append({})

    def leave_scope(self):
        self.fp_offsets.pop()
        self.proc_decls.pop()
        self.register_assignements = {}
        self.free_registers.clear()
        
    def write(self, text, indent='    '):
        print >> self.output_file, indent + text
        
    def create_call_label(self, title):
        label = '%s_%d' % (title, self.label_counts[title])
        self.label_counts[title] += 1
        return label
    
    def get_label(self, name):
        decl = self.get_proc_decl(name)
        if decl.is_global:
            # Mangle global procedure names so that their definitions can be
            # shadowed by local declarations later.
            return '__global_%s' % name.id
        return name.id
        
    def get_memory_location(self, name):
        if name in self.global_memory_locations:
            return str(self.global_memory_locations[name])
        elif self.current_fp_offset[name] < 0:
            dir = {p.var_decl.name:p.direction for p in 
                    self.get_proc_decl(self.current_procedure).params}[name]
            if dir == tokens.OUT:
                # Out parameters are passed by reference
                return 'MM[FP%d]' % self.current_fp_offset[name]
            else:
                # In parameters are passed by value
                return 'FP%d' % self.current_fp_offset[name]
        else:
            return 'FP + %d' % self.current_fp_offset[name]
        
    def get_register(self, node):
        try:
            return self.register_assignements[node]
        except KeyError:
            reg = self.free_registers.get()
            # TODO: this will load outparams unnecessarily
            value = 'MM[%s]' % self.get_memory_location(node)
            if self.generate_comments:
                self.write('%s = %s; /* %s */' % (reg, value, node.id))
            else:
                self.write('%s = %s;' % (reg, value))

            self.register_assignements[node] = reg
            return reg
        
    def calc_local_var_stack_size(self, node):
        sp_offset = 0
        for decl in node.decls:
            if isinstance(decl, syntaxtree.VarDecl):
                if decl.is_global:
                    # Since FP and SP both equal 0 at the start of the program,
                    # the the static memory location is the offset.
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
        # Add name to parent scope
        self.set_proc_decl(node.name, node)
        
        # Special case the runtime funcitons
        if node.name.id in runtime_functions:
            self.write('\n%s:' % node.name.id, indent='')
            self.write(runtime_functions[node.name.id])
            return

        self.enter_scope()

        # Add name to current scope to allow recursion
        self.set_proc_decl(node.name, node)
        self.current_procedure = node.name
        
        sp_offset = self.calc_local_var_stack_size(node) + len(node.params) + 2
        
        for i, param in enumerate(node.params, 2):
            self.current_fp_offset[param.var_decl.name] = -i
        
        self.write('\n%s:' % self.get_label(node.name), indent='')
        
        # Add to the offsets to account for the return address and the previous
        # FP.
        self.write('FP = SP + %d;' % (len(node.params) + 2))
        self.write('SP = SP + %d;' % (sp_offset))
        
        for statement in node.body:
            self.visit(statement)
            
        
        outparams = [p.var_decl.name for p in node.params
                        if p.direction == tokens.OUT]
        # Store live global variables and out parameters.
        live_vars = (r for r in self.register_assignements if
                r in outparams or r in self.global_memory_locations)
        self.store_variables(live_vars)
            
        if self.generate_comments:
            self.write('/* Unwind the stack. */')
            
        self.write('SP = FP - %d;' % (len(node.params) + 2))
        self.write('R[0] = MM[FP];')
        self.write('FP = MM[FP-1];')
        self.write('goto *(void *)R[0];')
        
        self.leave_scope()
        
    def visit_program(self, node):
        self.write(PROLOG, indent='')
        self.write('goto %s;' % node.name.id)

        sp_offset = self.calc_local_var_stack_size(node)
        
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
        
        # Translate the not operator into the C equivalent, which is dependent
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
        if (isinstance(node.value, syntaxtree.Num) and '.' in node.value.n or
            node.target.node_type == tokens.FLOAT):
            self.write('FLOAT_REG_1 = %s;' % value)
            self.write('memcpy(&%s, &FLOAT_REG_1, sizeof(float));' % outreg)
        else:
            self.write('%s = %s;' % (outreg, value))
        
        # Store array assignments immediately to save registers
        if isinstance(node.target, syntaxtree.Subscript):
            self.write('MM[%s] = %s;' % (self.last_subscript_address, outreg))
            self.free_registers.put(self.last_subscript_address)
        
        if self.allocated_register(node.value):
            self.free_registers.put(value)
        
    def visit_call(self, node):
        call_label = self.get_label(node.func)
        return_label = self.create_call_label('return_from_%s' % call_label)
        
        if self.generate_comments:
            line = node.func.token.line
            startpos = node.func.token.start
            endpos = line.index(';', startpos)
            self.write('/* %s */' % line[startpos:endpos])
        
        self.store_variables(self.register_assignements)
        
        
        # Push arguments right-to-left
        reg = self.free_registers.get()
        decl = self.get_proc_decl(node.func)
        for i, (arg, param) in enumerate(reversed(zip(node.args, decl.params))):
            if param.direction == tokens.OUT:
                self.write('%s = %s;' % (reg, self.get_memory_location(arg)))
                valuereg = reg
            else:
                valuereg = self.visit(arg)
            self.write('MM[SP + %d] = %s;' % (i + 1, valuereg))
        
        # Python loop variables are leaked into their surrounding scope (by design)
        self.write('MM[SP + %d] = FP;' % (i + 2))
        self.write('MM[SP + %d] = (int)&&%s;' % (i + 3, return_label))
        
        self.write('goto %s;' % call_label)
        self.write('\n%s:' % return_label, indent='')
            
        self.register_assignements.clear()
        
    def visit_if(self, node):
        test_reg = self.visit(node.test)
        endif_label = self.create_call_label('__endif')
        
        if node.orelse:
            target_label = self.create_call_label('__else')
        else:
            target_label = endif_label
        
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
        start_label = self.create_call_label('__for')
        end_label = self.create_call_label('__endfor')
        
        self.write('\n%s:' % start_label)
        # XXX: Putting the test blindly inside the label will cause the program
        # to load the variable from memory at the start of the loop, with
        # results in an infinite loop if the test variable is unreferenced
        # before the loop. Programs testing uninitialized variables are
        # ill formed anyway. A workaround would be to load all variables at the
        # start of a function.
        test_reg = self.visit(node.test)
        self.write('if (!%s) goto %s;' % (test_reg, end_label))
        
        for statement in node.body:
            self.visit(statement)
            
        self.write('\n%s:' % end_label)
        
        
if __name__ == '__main__':
    import argparse
    import scanner
    import parser
    import typechecker

    argparser = argparse.ArgumentParser(description='Test the type code generation functionality.')
    
    argparser.add_argument('filename', help='the file to parse')
    argparser.add_argument('-r', '--include-runtime', action='store_true',
                            help='include definitions of the runtime functions')
    #argparser.add_argument('-Vasm', '--verbose-assembly', action='store_true', default=False,
    #                       help='Add comments to the generated code')
    args = argparser.parse_args()

    ast = parser.parse_tokens(scanner.tokenize_file(args.filename),
                              include_runtime=args.include_runtime)
    if typechecker.tree_is_valid(ast):
        #import optimizer
        #optimizer.optimize_tree(ast, 2)
        CodeGenerator(generate_comments=True).walk(ast)
