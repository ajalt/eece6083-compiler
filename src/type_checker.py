import syntaxtree

class _Checker(syntaxtree.TreeWalker):
    def __init__(self):
        self.global_scope = {}
        self.scopes = [{}]

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
                raise Exception('Undefined call')

    def visit_program(self, node):
        for decl in node.decls:
            if isinstance(decl, (syntaxtree.VarDecl, syntaxtree.ProcDecl)):
                self.define_variable(decl.name, decl, decl.is_global)

    def visit_call(self, node):
        proc_decl = self.get_decl(node.name)

        self.enter_scope()

        for decl in node.decls:
            self.define_variable(decl.name, decl)
                   
    
    def visit_binop(self, node):
        pass

    def visit_unaryop(self, node):
        pass

def check_node(node):
    _Checker().walk(node)
