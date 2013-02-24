import collections

import syntaxtree
import tokens

_array_type = collections.namedtuple('_array_type', ['type', 'length'])

class _Checker(syntaxtree.TreeWalker):
    def __init__(self):
        super(_Checker, self).__init__()
        
        self.global_scope = {}
        self.scopes = [{}]
        
        self.visit_functions = {
            syntaxtree.Program:self.visit_program,
            syntaxtree.Assign:self.visit_assign,
            syntaxtree.ProcDecl:self.visit_procdecl,
            syntaxtree.Call:self.visit_call,
        }
        
        self.leave_functions = {
            syntaxtree.ProcDecl:self.leave_procdecl,
        }

    def enter_scope(self):
        self.scopes.append({})

    def leave_scope(self):
        self.scopes.pop()

    def define_variable(self, name, value, is_global=False):
        if is_global:
            scope = self.global_scope
        else:
            scope = self.scopes[-1]

        if name in scope:
            raise Exception('name %s already defined' % name)

        scope[name] = value

    def get_decl(self, name):
        try:
            return self.scopes[-1][name]
        except KeyError:
            try:
                return self.global_scope[name]
            except KeyError:
                raise Exception('Undefined id %r' % name)
            
    def get_type(self, node):
        if isinstance(node, syntaxtree.BinaryOp):
            type = self.unify_types(node.left, node.right)
            if type != tokens.INT and node.op in (tokens.AND, tokens.OR, tokens.NOT):
                raise Exception('Bitwise operators only valid on integers')
            if type not in (tokens.INT, tokens.FLOAT):
                raise Exception('Operators only valid on numbers')
            return type
            
        if isinstance(node, syntaxtree.UnaryOp):
            return self.get_type(node.operand)
        
        if isinstance(node, syntaxtree.Num):
            return tokens.FLOAT if '.' in node.n else tokens.INT
        
        if isinstance(node, syntaxtree.Name):
            return self.get_decl(node).type
        
        if isinstance(node, syntaxtree.Subscript):
            decl = self.get_decl(node.name)
            return _array_type(decl.type, decl.array_length)
        
        if isinstance(node, syntaxtree.Str):
            return tokens.STRING_TYPE
        
    def unify_types(self, a, b):
        type_a = self.get_type(a)
        type_b = self.get_type(b)
        
        if isinstance(type_a, _array_type):
            type_a = type_a.type
        if isinstance(type_b, _array_type):
            type_b = type_b.type
            
        if type_a == type_b:
            return type_a
        if set((type_a, type_b)) == set((tokens.INT, tokens.FLOAT)):
            return tokens.FLOAT
        raise Exception('Cannot unify %r and %r' % (type_a, type_b))
    
        print a,b,type_a,type_b

    def visit_program(self, node):
        for decl in node.decls:
            self.define_variable(decl.name, decl, decl.is_global)

    def visit_call(self, node):
        proc_decl = self.get_decl(node.name)
        
        if len(node.args) != len(proc_decl, params):
            raise Exception('Wrong number of args')
        
        for arg, param in zip(node.args, proc_decl.params):
            self.unify_types(arg, param.var_decl)
            
    def visit_assign(self, node):
        self.unify_types(node.target, node.value)
    
    def visit_procdecl(self, node):
        self.enter_scope()
        for decl in node.decls:
            if decl.is_global:
                raise Exception('Can only declare global variables at top level scope.')
            self.define_variable(decl.name, decl)
        
    def leave_procdecl(self, node):
        self.leave_scope()
        
        
def check_node(node):
    _Checker().walk(node)
    
if __name__ == '__main__':
    import argparse
    import parser
    import scanner
    
    argparser = argparse.ArgumentParser(description='Test the type checking functionality.')
    
    argparser.add_argument('filename', help='the file to parse')
    args = argparser.parse_args()
    
    check_node(parser.parse_tokens(scanner.tokenize_file(args.filename)))

