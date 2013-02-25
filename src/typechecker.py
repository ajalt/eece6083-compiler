import syntaxtree
import tokens

class _Checker(syntaxtree.TreeWalker):
    def __init__(self):
        super(_Checker, self).__init__()
        
        self.global_scope = {}
        self.scopes = [{}]
        
        self.error_encountered = False
        
        self.visit_functions = {
            syntaxtree.Program:self.visit_program,
            syntaxtree.Assign:self.visit_assign,
            syntaxtree.ProcDecl:self.visit_procdecl,
            syntaxtree.Call:self.visit_call,
        }
        
        self.leave_functions = {
            syntaxtree.ProcDecl:self.leave_procdecl,
        }
        
    def report_error(self, msg, token=None):
        self.error_encountered = True
        if token:
            underline = '^' if token.start == token.end else '~'
            line = token.line.rstrip()
            print ('Error on line %s: %s\n'
                    '    %s\n'
                    '    %s') % (token.lineno, msg, line,
                                 ''.join((underline if token.start <= i <= token.end else ' ')
                                            for i in xrange(len(line))))
        else:
            print msg

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
            self.report_error('Name %r already defined' % name, name.token)
            return
        
        if isinstance(value, syntaxtree.VarDecl) and value.array_length is not None:
            # Record the declaration even if it's incorrect, so that we don't
            # get generate spurious error when the name is referenced.
            array_length_type = self.get_type(value.array_length)
            if array_length_type != tokens.INT:
                self.report_error('Size of array has non-integer type %r' % array_length_type, value.array_length.token)
        scope[name] = value

    def get_decl(self, name):
        try:
            return self.scopes[-1][name]
        except KeyError:
            try:
                return self.global_scope[name]
            except KeyError:
                self.report_error('Undefined identifier %r' % name, name.token)
                return None
            
    def get_type(self, node):
        if isinstance(node, syntaxtree.BinaryOp):
            type = self.unify_types(node.left, node.right)
            if type is None:
                return None
            if type != tokens.INT and node.op in (tokens.AND, tokens.OR, tokens.NOT):
                self.report_error('Bitwise operators only valid on integers, not %r' % type, node.token)
            elif type not in (tokens.INT, tokens.FLOAT):
                self.report_error('Operator %r only valid on numbers' % node.op, node.token)
            return type
            
        if isinstance(node, syntaxtree.UnaryOp):
            return self.get_type(node.operand)
        
        if isinstance(node, syntaxtree.Num):
            return tokens.FLOAT if '.' in node.n else tokens.INT
        
        if isinstance(node, syntaxtree.Name):
            decl = self.get_decl(node)
            if decl is None:
                return None
            return decl.type
        
        if isinstance(node, syntaxtree.Subscript):
            decl = self.get_decl(node.name)
            if decl is None:
                return None
            if not isinstance(decl, syntaxtree.VarDecl) or decl.array_length is None:
                self.report_error('Subscripted value is not an array', node.token)
                return None
            if self.get_type(node.index) != tokens.INT:
                self.report_error('Array index is not an integer', node.token)
                return None
            return decl.type
        
        if isinstance(node, syntaxtree.Str):
            return tokens.STRING_TYPE
        
    def unify_types(self, a, b):
        type_a = self.get_type(a)
        type_b = self.get_type(b)
        
        # The error in this expression was already reported, don't report
        # extraineous errors.
        if None in (type_a, type_b):
            return None
        
        if type_a == tokens.BOOL:
            type_a = tokens.INT
        if type_b == tokens.BOOL:
            type_b = tokens.INT
        
        if type_a == type_b:
            return type_a
        
        if set((type_a, type_b)) == set((tokens.INT, tokens.FLOAT)):
            return tokens.FLOAT
        
        # Improve the error printout a little by giving the output a better range
        if a.token is not None and b.token is not None:
            token = a.token._replace(end=b.token.end)
        else:
            token = a.token
        self.report_error('Incompatible types %r and %r' % (type_a, type_b), token)
    
    def visit_program(self, node):
        for decl in node.decls:
            self.define_variable(decl.name, decl, decl.is_global)

    def visit_call(self, node):
        proc_decl = self.get_decl(node.func)
        
        if len(node.args) != len(proc_decl.params):
            self.report_error('Procedure %r takes exactly %s arguments (%s given)' %
                             (node.func.id, len(proc_decl.params), len(node.args)), node.token)
        
        for arg, param in zip(node.args, proc_decl.params):
            self.unify_types(arg, param.var_decl)
            
    def visit_assign(self, node):
        self.unify_types(node.target, node.value)
    
    def visit_procdecl(self, node):
        self.enter_scope()
        for decl in node.decls:
            if decl.is_global:
                self.report_error('Can only declare global identifiers at top level scope.', decl.name.token)
            self.define_variable(decl.name, decl)
        
    def leave_procdecl(self, node):
        self.leave_scope()
        
def tree_is_valid(node):
    checker = _Checker()
    checker.walk(node)
    return not checker.error_encountered
    
if __name__ == '__main__':
    import argparse
    import parser
    import scanner
    
    argparser = argparse.ArgumentParser(description='Test the type checking functionality.')
    
    argparser.add_argument('filename', help='the file to parse')
    args = argparser.parse_args()
    
    print tree_is_valid(parser.parse_tokens(scanner.tokenize_file(args.filename)))

