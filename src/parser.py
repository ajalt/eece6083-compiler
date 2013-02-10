'''Create an Abstract Syntax Tree from an iterable of tokens.

The types of nodes in the tree are defined in the syntaxtree module. The parser
prints errors to stdout, and has several resync points to continue parsing if it
encounters a syntax error. however, once parsing is finished, if any errors were
encountered, a ParseFailedError is raised, indicating that the source could not
be parsed.'''

import itertools

import tokens
import scanner
import syntaxtree

class ParseError(Exception):
    def __init__(self, msg, token):
        self.msg = msg
        self.token = token
    
    def __str__(self):
        underline = '^' if self.token.start == self.token.end else '~'
        line = self.token.line.rstrip()
        return ('Error on line %s: %s\n'
                '    %s\n'
                '    %s') % (self.token.lineno, self.msg, line,
                             ''.join((underline if self.token.start <= i <= self.token.end else ' ')
                                        for i in xrange(len(line))))
    
    def __repr__(self):
        return 'ParseError(msg=%r, token=%r)' % (self.msg, self.token)
    
class ParseFailedError(Exception): pass

class _Parser(object):
    def __init__(self, token_stream):
        # tee will take care of caching the iterator so that we can get the lookahead
        self.token = None
        self.next_token = None
        
        # This will iterate over both of the iterators returned by tee in parallel
        # next_token will be None when token is the last token in the stream.
        iterators = itertools.tee(token_stream)
        # Advance the second iterator returned by tee, which will be the lookahead.
        next(iterators[1])
        self._token_iter = itertools.izip_longest(*iterators)
        
        # Set up the expression parser. We have to define this all here because
        # the classes need access to the tokens and expression function.
        class Symbol(object):
            precedence = 0
            parser = self
            
            def __init__(self, id):
                self.id = id
            
            def prefix(self):
                raise ParseError("Unexpected '%s' in expression" % self.id, self.parser.token)
            
            def infix(self, left_term):
                raise ParseError("Unexpected '%s' in expression" % self.id, self.parser.token)

            
        class Number(Symbol):
            precedence = 0
            
            def __init__(self, value):
                self.value = value
            
            def prefix(self):
                return syntaxtree.Num(self.value)
            
        class Identifier(Symbol):
            precedence = 0
            
            def __init__(self, id):
                self.id = id
            
            def prefix(self):
                return syntaxtree.Name(self.id)

        class String(Symbol):
            precedence = 0

            def __init__(self, s):
                self.s = s

            def prefix(self):
                return syntaxtree.Str(self.s)
            
        class TrueVal(Symbol):
            def prefix(self):
                return tokens.TRUE
            
        class FalseVal(Symbol):
            def prefix(self):
                return tokens.FALSE
            
        class InfixOperator(Symbol):
            def __init__(self, id, precedence):
                self.id = id
                self.precedence = precedence
                
            def infix(self, left_term):
                return syntaxtree.BinaryOp(self.id, left_term, self.parser.expression(self.precedence))
            
        class PrefixOperator(Symbol):
            def __init__(self, id, precedence):
                self.id = id
                self.precedence = precedence
                
            def prefix(self):
                return syntaxtree.UnaryOp(self.id, self.parser.expression(self.precedence))
            
        class Minus(InfixOperator):
            def __init__(self, infix_precedence, prefix_precedence):
                super(Minus, self).__init__(tokens.MINUS, infix_precedence)
                self.prefix_precedence = prefix_precedence
                
            def prefix(self):
                return syntaxtree.UnaryOp(tokens.MINUS, self.parser.expression(self.prefix_precedence))
            
        class OpenParen(Symbol):
            def __init__(self, precedence):
                self.precedence = precedence
                
            def prefix(self):
                # Grouping
                exp = self.parser.expression()
                self.parser.match(tokens.CLOSEPAREN)
                return exp
            
            def infix(self, left_term):
                # Function call
                function_name = left_term
                function_args = []
                if self.parser.next_token.type != tokens.CLOSEPAREN:
                    function_args.append(self.parser.expression())
                    while self.parser.next_token.type == tokens.COMMA:
                        self.parser.advance_token()
                        function_args.append(self.parser.expression())
                self.parser.match(tokens.CLOSEPAREN)
                return syntaxtree.Call(function_name, function_args)
               
        class OpenBracket(Symbol):
            def __init__(self, precedence):
                self.precedence = precedence
                
            def infix(self, left_term):
                # Array Index
                index = self.parser.expression()
                self.parser.match(tokens.CLOSEBRACKET)
                return syntaxtree.Subscript(left_term, index) 

        #  expression_operators is a map of tokens types to symbol classes. If a
        #  token is encountered that is not valid in an expression, the map will
        #  populate itself with a new entry that will end the expression or
        #  raise an error if the expression is not in a valid state. 
        class OperatorMap(dict):
            def __missing__(self, key):
                self[key] = Symbol(key)
                return self[key]
            
        self.expression_operators = OperatorMap({
            tokens.NUMBER: Number,
            tokens.IDENTIFIER: Identifier,
            tokens.STRING: String,
            tokens.TRUE: TrueVal(tokens.TRUE),
            tokens.FALSE: FalseVal(tokens.FALSE),
            tokens.CLOSEPAREN: Symbol(tokens.CLOSEPAREN),
            tokens.COMMA: Symbol(tokens.COMMA),
            tokens.CLOSEBRACKET: Symbol(tokens.CLOSEBRACKET),
            tokens.OR: InfixOperator(tokens.OR, 1),
            tokens.AND: InfixOperator(tokens.AND, 1),
            tokens.NOT: PrefixOperator(tokens.NOT, 1),
            tokens.PLUS: InfixOperator(tokens.PLUS, 2),
            tokens.MINUS: Minus(2, 7),
            tokens.LT: InfixOperator(tokens.LT, 3),
            tokens.GTE: InfixOperator(tokens.GTE, 3),
            tokens.LTE: InfixOperator(tokens.LTE, 3),
            tokens.GT: InfixOperator(tokens.GT, 3),
            tokens.EQUAL: InfixOperator(tokens.EQUAL, 3),
            tokens.NOTEQUAL: InfixOperator(tokens.NOTEQUAL, 3),
            tokens.MULTIPLY: InfixOperator(tokens.MULTIPLY, 4),
            tokens.DIVIDE: InfixOperator(tokens.DIVIDE, 4),
            tokens.OPENPAREN: OpenParen(5),
            tokens.OPENBRACKET: OpenBracket(5),
        })
                
    
    def get_symbol(self, token):
        if token.type in (tokens.NUMBER, tokens.IDENTIFIER, tokens.STRING):
            return self.expression_operators[token.type](token.token)
        return self.expression_operators[token.type]
    
    @property
    def current_symbol(self):
        return self.get_symbol(self.token)
    
    @property
    def next_symbol(self):
        return self.get_symbol(self.next_token)
        
    def advance_token(self):
        self.token, self.next_token = next(self._token_iter)
        
    def match(self, token_type):
        if self.next_token is not None and self.next_token.type == tokens.EOF:
            # If we see an unexpected EOF, return the last token in the stream
            # with the start and end points set to the end of the line.
            raise ParseError('Unexpected EOF found', self.token._replace(start=self.token.end))
        
        self.advance_token()

        if self.token.type != token_type:
            raise ParseError('Expected %r, found %r' % (token_type, self.token.type), self.token)
    
    def _consume_optional_token(self, tok):
        if self.token.type == tok:
            self.advance_token()
            return True
        return False
    
    def parse(self):
        # program
        try:
            # progarm header
            self.match(tokens.PROGRAM)
            self.match(tokens.IDENTIFIER)
            name = syntaxtree.Name(self.token.token)
            self.match(tokens.IS)
            
            # program body
            decls = self.declarations()
            self.match(tokens.BEGIN)
            body = self.statements()
            self.match(tokens.END)
            self.match(tokens.PROGRAM)
            
            return syntaxtree.Program(name, decls, body)
        
        except ParseError as err:
            print err
    
    def expression(self, precedence=0):
        self.advance_token()
        
        left_term = self.current_symbol.prefix()
        
        while precedence < self.next_symbol.precedence:
            self.advance_token()
            left_term = self.current_symbol.infix(left_term)
        
        return left_term
    
    def declarations(self):
        declarations = []
        while self.next_token.type != tokens.BEGIN:
            try:
                declarations.append(self.declaration())
            except ParseError as err:
                print err
            self.match(tokens.SEMICOLON)
        return declarations
            
    def declaration(self):
        self.advance_token()
        if self.token.type == tokens.PROCEDURE or self.next_token.type == tokens.PROCEDURE:
            return self.procedure_declaration()
        return self.variable_declaration()
    
    def parameter(self):
        self.advance_token()
        decl = self.variable_declaration()
        self.advance_token()
        if self.token.type not in (tokens.IN, tokens.OUT):
            # We could resync here.
            raise ParseError('Direction missing from parameter specification', self.token)
        direction = self.token.type
        return syntaxtree.Param(decl, direction)
    
    def procedure_declaration(self):
        is_global = self._consume_optional_token(tokens.GLOBAL)
        
        if self.token.type != tokens.PROCEDURE:
            raise ParseError('Expected %r, found %r' % (tokens.PROCEDURE, self.token.type), self.token)
        
        self.match(tokens.IDENTIFIER)
        name = syntaxtree.Name(self.token.token)

        # Parameter list
        self.match(tokens.OPENPAREN)
        
        parameters = []
        if self.next_token.type != tokens.CLOSEPAREN:
            parameters.append(self.parameter())
            while self.next_token.type == tokens.COMMA:
                self.advance_token()
                parameters.append(self.parameter())
        
        self.match(tokens.CLOSEPAREN)
            
        # local variable declarations
        var_decls = self.declarations()
        
        # Body
        self.match(tokens.BEGIN)
        body = self.statements()
        self.match(tokens.END)
        self.match(tokens.PROCEDURE)
        
        return syntaxtree.ProcDecl(is_global, name, parameters, var_decls, body)
            
            
    def variable_declaration(self):
        is_global = self._consume_optional_token(tokens.GLOBAL)
        if self.token.type in (tokens.INT, tokens.FLOAT, tokens.BOOL, tokens.STRING_KEYWORD):
            type_mark = self.token.type
        else:
            raise ParseError('Expected type mark, found %s' % self.token.type, self.token)
        
        self.match(tokens.IDENTIFIER)
        name = syntaxtree.Name(self.token.token)
        
        if self.next_token.type == tokens.OPENBRACKET:
            self.advance_token()
            self.match(tokens.NUMBER)
            array_size = self.token.token
            self.match(tokens.CLOSEBRACKET)
        else:
            array_size = None
            
        return syntaxtree.VarDecl(is_global, type_mark, name, array_size)
    
    def statements(self):
        '''Return a list of zero or more statement nodes'''
        statements = []
        while self.next_token.type not in (tokens.END, tokens.ELSE):
            try:
                statements.append(self.statement())
            except ParseError as err:
                print err
            self.match(tokens.SEMICOLON)
        return statements
    
    def statement(self):
        self.advance_token()
        # these calls can't all be inlined, since for_statement calls
        # assignment_statement specificly, and there's no reason to make that a
        # special case.
        if self.token.type == tokens.IF:
            return self.if_statement()
        if self.token.type == tokens.FOR:
            return self.for_statement()
        if self.token.type == tokens.RETURN:
            return tokens.RETURN
        return self.assignment_statement()
    
    def assignment_statement(self):
        if self.token.type != tokens.IDENTIFIER:
            raise ParseError('Target of assignment must be a variable, not %s' % self.token.token, self.token)
        
        target = syntaxtree.Name(self.token.token)
        self.match(tokens.ASSIGN)
        value = self.expression()
        return syntaxtree.Assign(target, value)
    
    def if_statement(self):
        self.match(tokens.OPENPAREN)
        test = self.expression()
        self.match(tokens.CLOSEPAREN)
        
        self.match(tokens.THEN)
        
        # at least one statement is required in the then clause
        body = [self.statement()]
        self.match(tokens.SEMICOLON)
        body += self.statements()
        
        if self.next_token.type == tokens.ELSE:
            self.advance_token()
            
            # one or more statements are required in the else clause as well
            orelse = [self.statement()]
            self.match(tokens.SEMICOLON)
            orelse += self.statements()
        else:
            orelse = []
            
        self.match(tokens.END)
        self.match(tokens.IF)
        
        return syntaxtree.If(test, body, orelse)
    
    def for_statement(self):
        self.match(tokens.OPENPAREN)
        # advance past the '(' token here, since all of the specific *_statement
        # functions expect the current token to be the start of their production
        self.advance_token()
        assignment = self.assignment_statement()
        self.match(tokens.SEMICOLON)
        
        test = self.expression()
        self.match(tokens.CLOSEPAREN)
        
        body = self.statements()
        self.match(tokens.END)
        self.match(tokens.FOR)
        
        return syntaxtree.For(assignment, test, body)
        

def parse_tokens(token_stream):
    '''Return an ast created from an iterable of tokens.
    
    A node of type syntaxtree.Program will be returned, or a ValueError will be
    raised in the case of a syntax error in the input tokens.
    '''
    return _Parser(token_stream).parse()
    
    
if __name__ == '__main__':
    def print_expression(node):
        if isinstance(node, syntaxtree.BinaryOp):
            print '(',
            print_expression(node.left)
            print node.id,
            print_expression(node.right)
            print ')',
        elif isinstance(node, syntaxtree.Num):
            print node.n,
        elif isinstance(node, syntaxtree.Name):
            print node.id,

        
    #s = '''
    #program p is
    #    float x;
    #    string y[2];
    #begin
    #
    #end program
    #'''
    #parse = parse_tokens(scanner.tokenize_string((s)))
    #print parse
    #print_expression(parse)
    
    s = '1 + 2'
    print _Parser(scanner.tokenize_file('../test/test_program.src')).parse()
    
