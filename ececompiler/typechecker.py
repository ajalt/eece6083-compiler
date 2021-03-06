'''Perform semantic validation of a syntactically valid AST.

The typechecker module validates trees of AST nodes generated by the parser.

The tree_is_valid() function takes the ast root node as an argument, and returns
True if there are no semantic errors in the tree. If any errors are encountered,
they are printed and False is returned.
'''

import syntaxtree
import tokens

class TypeCheckError(Exception):
    def __init__(self, msg, token=None):
        self.msg = msg
        self.token = token
    
    def __str__(self):
        if self.token:
            underline = '^' if self.token.start == self.token.end else '~'
            line = self.token.line.rstrip()
            return ('Error on line %s: %s\n'
                    '    %s\n'
                    '    %s') % (self.token.lineno, self.msg, line,
                                 ''.join((underline if self.token.start <= i <= self.token.end else ' ')
                                            for i in xrange(len(line))))
        else:
            return self.msg
            
    def __repr__(self):
        return 'TypeCheckError(msg=%r, token=%r)' % (self.msg, self.token)

class Checker(syntaxtree.TreeWalker):
    def __init__(self):
        super(Checker, self).__init__()
        
        self.global_scope = {}
        self.scopes = [{}]
        
        self.error_encountered = False
        
        self.visit_functions = {
            syntaxtree.Program:self.visit_program,
            syntaxtree.Assign:self.visit_assign,
            syntaxtree.ProcDecl:self.visit_procdecl,
            syntaxtree.Call:self.visit_call,
        }
        
    def report_error(self, err):
        self.error_encountered = True
        print err

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
            self.report_error(TypeCheckError('Name %r already defined' % name, name.token))
        
        if isinstance(value, syntaxtree.VarDecl) and value.array_length is not None:
            # Record the declaration even if it's incorrect, so that we don't
            # generate spurious error when the name is referenced.
            array_length_type = self.get_type(value.array_length)
            if array_length_type != tokens.INT:
                self.report_error(TypeCheckError('Size of array has non-integer type %r' % array_length_type, value.array_length.token))
        scope[name] = value

    def get_decl(self, name):
        ''' Return the symbol table entry for a given Node, or raise an error if it's undefined.
        '''
        if isinstance(name, syntaxtree.Name):
            key = name
        elif isinstance(name, syntaxtree.Subscript):
            key = name.name
        else:
            raise TypeCheckError('Expected an identifier', name.token)
        
        try:
            return self.scopes[-1][key]
        except KeyError:
            try:
                return self.global_scope[key]
            except KeyError:
                raise TypeCheckError('Undefined identifier %r' % key, key.token)
            
    def get_type(self, node):
        '''Return the type of a given Node instance, or raise an error if it is invalid.
        '''
        type = None
        if isinstance(node, syntaxtree.BinaryOp):
            type = self.unify_node_types(node.left, node.right)
            if type not in (tokens.BOOL, tokens.INT) and node.op in (tokens.AND, tokens.OR, tokens.NOT):
                raise TypeCheckError('Bitwise operators only valid on integers, not %r' % type, node.token)
            elif type not in (tokens.INT, tokens.FLOAT, tokens.BOOL):
                raise TypeCheckError('Operator %r only valid on numbers' % node.op, node.token)
            
        elif isinstance(node, syntaxtree.UnaryOp):
            type = self.get_type(node.operand)
            if type == tokens.FLOAT and node.op == tokens.NOT:
                raise TypeCheckError("Operator 'not' is not valid on floats", node.token)
        
        elif isinstance(node, syntaxtree.Num):
            if node.n in (tokens.TRUE, tokens.FALSE):
                type = tokens.BOOL
            else:
                type = tokens.FLOAT if '.' in node.n else tokens.INT
        
        elif isinstance(node, syntaxtree.Name):
            decl = self.get_decl(node)
            if isinstance(decl, syntaxtree.Param):
                if decl.direction != tokens.IN:
                    raise TypeCheckError('Cannot read from out parameter', node.token)
                type = decl.var_decl.type
            elif isinstance(decl, syntaxtree.ProcDecl):
                raise TypeCheckError('Identifier %r is a procedure, not a variable' % node.id, node.token)
            else:
                type = decl.type
        
        elif isinstance(node, syntaxtree.Subscript):
            decl = self.get_decl(node.name)
            if isinstance(decl, syntaxtree.Param):
                decl = decl.var_decl
            if not isinstance(decl, syntaxtree.VarDecl) or decl.array_length is None:
                raise TypeCheckError('Subscripted value is not an array', node.token)
            if self.get_type(node.index) != tokens.INT:
                raise TypeCheckError('Array index is not an integer', node.token)
            type = decl.type
        
        elif isinstance(node, syntaxtree.Str):
            type = tokens.STRING_TYPE
        
        if type:
            node.node_type = type
            return type
        raise TypeCheckError('Unknown type', node.token)
        
    def unify_node_types(self, node_a, node_b):
        '''Return the a type able to represent the types of both Nodes, or raise an error if the types are not compatible.
        '''
        
        # This complicated chunk of error handling allows us to print errors for
        # both nodes in order.
        try:
            type_a = self.get_type(node_a)
        except TypeCheckError as err:
            try:
                type_b = self.get_type(node_b)
            except TypeCheckError as err2:
                self.report_error(err)
                raise err2
            else:
                raise err
        else:
            type_b = self.get_type(node_b)
        
        try:
            return self.unify_types(type_a, type_b)
        except TypeCheckError:
            # Improve the error printout a little by giving the output a better range
            if node_a.token is not None and node_b.token is not None:
                token = node_a.token._replace(end=node_b.token.end)
            else:
                token = node_a.token
            raise TypeCheckError('Incompatible types %r and %r' % (type_a, type_b), token)
        
    def unify_types(self, type_a, type_b):
        '''Return a type able to represent both given types, or raise an error if they are not compatible.
        '''
        if type_a == type_b:
            return type_a
        
        if set((type_a, type_b)) == set((tokens.INT, tokens.FLOAT)):
            return tokens.FLOAT
        if set((type_a, type_b)) == set((tokens.INT, tokens.BOOL)):
            return tokens.BOOL
        
        raise TypeCheckError('Incompatible types %r and %r' % (type_a, type_b))
    
    # All of the following visit_* functions are called by the NodeWalker parent
    # class. They are responsible for initiating all the type checking and
    # ensuring that no TypeCheckErrors propagate past their scope.
    
    def visit_program(self, node):
        for decl in node.decls:
            self.define_variable(decl.name, decl, decl.is_global)
            
        self.visit_children(node)

    def visit_call(self, node):
        try:
            proc_decl = self.get_decl(node.func)
        except TypeCheckError as err:
            self.report_error(err)
        else:
            if len(node.args) != len(proc_decl.params):
                self.report_error(TypeCheckError(
                    'Procedure %r takes exactly %s arguments (%s given)' %
                        (node.func.id, len(proc_decl.params), len(node.args)),node.token))
            
            for arg, param in zip(node.args, proc_decl.params):
                if param.direction == tokens.OUT:
                    if not isinstance(arg, syntaxtree.Name):
                        self.report_error(TypeCheckError(
                            'Argument to out parameter must be an identifier.', arg.token))
                        continue
                    try:
                        decl = self.get_decl(arg)
                    except TypeCheckError as err:
                        self.report_error(err)
                    else:
                        if isinstance(decl, syntaxtree.Param):
                            if decl.direction == tokens.OUT:
                                # Allow forwarding of out parameters
                                continue
                try:
                    argtype = self.get_type(arg)
                except TypeCheckError as err:
                    self.report_error(err)
                else:
                    try:
                        self.unify_types(argtype, param.var_decl.type)
                    except TypeCheckError:
                        self.report_error(TypeCheckError('Argument type %r does not match parameter type %r' %
                                          (argtype, param.var_decl.type), arg.token))
                
    def visit_assign(self, node):
        try:
            # node.target is guaranteed by the parser to be a Name or Subscript node.
            target_decl = self.get_decl(node.target)
            if isinstance(target_decl, syntaxtree.Param):
                if target_decl.direction == tokens.IN:
                    self.report_error(TypeCheckError('Cannot assign to input parameter', node.target.token))
                self.unify_types(target_decl.var_decl.type, self.get_type(node.value))
                node.target.node_type = target_decl.var_decl.type
            else:
                self.unify_node_types(node.target, node.value)
        except TypeCheckError as err:
            self.report_error(err)
    
    def visit_procdecl(self, node):
        self.enter_scope()
        
        # Add procedure name to scope to allow recursion.
        self.define_variable(node.name, node)
        # Add parameters to scope.
        for param in node.params:
            self.define_variable(param.var_decl.name, param)
        # Add local variables to scope.
        for decl in node.decls:
            if decl.is_global:
                self.report_error(TypeCheckError('Can only declare global identifiers at top level scope.', decl.name.token))
            self.define_variable(decl.name, decl)
            
        self.visit_children(node)
            
        self.leave_scope()
        
def tree_is_valid(node):
    '''Validate an Abstract Syntax Tree.
    
    Returns True if there are no semantic errors in the tree. If any errors are
    encountered, they are printed to stdout and False is returned.
    '''
    checker = Checker()
    checker.walk(node)
    return not checker.error_encountered
    
if __name__ == '__main__':
    import argparse
    import parser
    import scanner
    
    argparser = argparse.ArgumentParser(description='Test the type checking functionality.')
    
    argparser.add_argument('filename', help='the file to parse')
    args = argparser.parse_args()
    
    if tree_is_valid(parser.parse_tokens(scanner.tokenize_file(args.filename))):
        print 'Program is valid.'
