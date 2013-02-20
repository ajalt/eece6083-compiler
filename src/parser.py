'''Create an Abstract Syntax Tree from an iterable of tokens.

The types of nodes in the tree are defined in the syntaxtree module. The parser
prints errors to stdout, and has several resync points to continue parsing if it
encounters a syntax error. however, once parsing is finished, if any errors were
encountered, a ParseFailedError is raised, indicating that the source could not
be parsed.'''
# The parser uses a combination of recursive descent and top-down operator
# precedence. This is a similar strategy to gcc's c and c++ parsers, although
# they use precedence climbing instead of TDOP.
#
# Statements all use straight-forward recursive descent on the BNF, which was
# rewritten to remove left-recursion.
# 
# The TDOP section of the parser is used for all expressions, and is based on
# the following paper:
#
# Vaughan R. Pratt. 1973. Top down operator precedence. In Proceedings of the 1st
# annual ACM SIGACT-SIGPLAN symposium on Principles of programming languages (POPL
# '73). ACM, New York
#
# The expression() method implements Pratt's core state machine, although it
# takes advantage of Python's first-order classes to make the implementation
# cleaner. Pratt's led functions correspond to infix() methods on symbol
# classes, and his nud functions correspond to prefix() methods. The lbp has
# been renamed precedence. The expression_operators map takes advantage of
# autovivification (the __missing__ method of dicts) to remove the need to define
# all possible terminal symbols that can occur in an expression.

import itertools
import contextlib

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
        self.error_encountered = False
        
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
            
            def __init__(self, value):
                self.value = value
            
            def prefix(self):
                raise ParseError("Unexpected '%s' in expression" % self.value, self.parser.token)
            
            def infix(self, left_term):
                raise ParseError("Unexpected '%s' in expression" % self.value, self.parser.token)

            
        class Number(Symbol):
            def prefix(self):
                return syntaxtree.Num(self.value)
            
        class Identifier(Symbol):
            def prefix(self):
                return syntaxtree.Name(self.value)

        class String(Symbol):
            def prefix(self):
                return syntaxtree.Str(self.value)
            
        class TrueVal(Symbol):
            def prefix(self):
                return tokens.TRUE
            
        class FalseVal(Symbol):
            def prefix(self):
                return tokens.FALSE
            
        class Operator(Symbol):
            def __init__(self, value, precedence):
                self.value = value
                self.precedence = precedence
            
        class InfixOperator(Operator):
            def infix(self, left_term):
                return syntaxtree.BinaryOp(self.value, left_term, self.parser.expression(self.precedence))
            
        class PrefixOperator(Operator):
            def prefix(self):
                return syntaxtree.UnaryOp(self.value, self.parser.expression(self.precedence))
            
        class Minus(InfixOperator):
            def __init__(self, infix_precedence, prefix_precedence):
                self.value = tokens.MINUS
                self.precedence = infix_precedence
                self.prefix_precedence = prefix_precedence
                
            def prefix(self):
                return syntaxtree.UnaryOp(tokens.MINUS, self.parser.expression(self.prefix_precedence))
            
        class OpenParen(Symbol):
            def __init__(self, precedence):
                self.value = tokens.OPENPAREN
                self.precedence = precedence
                
            def prefix(self):
                # Grouping
                exp = self.parser.expression()
                self.parser.match(tokens.CLOSEPAREN)
                return exp
            
            # Function calls are no longer allowed inside statements.
            #def infix(self, left_term):
            #    # Function call
            #    function_name = left_term
            #    function_args = []
            #    if self.parser.next_token.type != tokens.CLOSEPAREN:
            #        function_args.append(self.parser.expression())
            #        while self.parser.next_token.type == tokens.COMMA:
            #            self.parser.advance_token()
            #            function_args.append(self.parser.expression())
            #    self.parser.match(tokens.CLOSEPAREN)
            #    return syntaxtree.Call(function_name, function_args)
               
        class OpenBracket(Symbol):
            def __init__(self, precedence):
                super(OpenBracket, self).__init__(tokens.OPENBRACKET)
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
        if self.token.type == tokens.ERROR:
            raise ParseError(self.token.token, self.token)
        return self.expression_operators[token.type]
    
    @property
    def current_symbol(self):
        return self.get_symbol(self.token)
    
    @property
    def next_symbol(self):
        return self.get_symbol(self.next_token)
        
    def advance_token(self):
        self.token, self.next_token = next(self._token_iter)
        
    def match(self, token_type, custom_exception=None):
        '''Advance the current token and check that it is the correct type'''
        if self.next_token is not None and self.next_token.type == tokens.EOF:
            # If we see an unexpected EOF, return the last token in the stream
            # with the start and end points set to the end of the line.
            raise ParseError('Unexpected EOF found', self.token._replace(start=self.token.end))
        
        self.advance_token()
        
        if self.token.type == tokens.ERROR:
            raise ParseError(self.token.token, self.token)

        if self.token.type != token_type:
            if custom_exception is not None:
                raise custom_exception
            raise ParseError('Expected %r, found %r' % (token_type, self.token.type), self.token)
    
    def _consume_optional_token(self, tok):
        if self.token.type == tok:
            self.advance_token()
            return True
        return False
    
    @contextlib.contextmanager
    def resync_point(self, followset):
        # Append EOF to the followset so that we don't go off the end of the
        # file trying to find a token that matches.
        if isinstance(followset, basestring):
            followset = [followset, tokens.EOF]
        else:
            followset.append(tokens.EOF)
            
        try:
            yield
        except ParseError as err:
            print err
            self.error_encountered = True
            while self.next_token.type not in followset:
                self.advance_token()
                if self.token.type == tokens.ERROR:
                    # Print the error and keep going.
                    print ParseError(self.token.token, self.token)
    
    def parse(self):
        '''Parse a complete program and return an ast.'''
        # program
        try:
            # program header
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
            
            if self.error_encountered:
                raise ParseFailedError('Errors encountered when parsing')
            
            return syntaxtree.Program(name, decls, body)
        except ParseError as err:
            print err
            raise ParseFailedError('Errors encountered when parsing')
    
    def expression(self, precedence=0):
        self.advance_token()
        
        left_term = self.current_symbol.prefix()
        
        # This will left-associate operators of the same precedence, or return a
        # sub-expression to operators of higher precedence.
        while precedence < self.next_symbol.precedence:
            self.advance_token()
            left_term = self.current_symbol.infix(left_term)
        
        return left_term
    
    def declarations(self):
        ''' Return a list of zero or more declaration nodes.'''
        # This handles the rule ::= (<declaration>)* by returning a possibly empty list.
        declarations = []
        # BEGIN is the follow-set for multiple declarations
        while self.next_token.type not in (tokens.BEGIN, tokens.EOF):
            with self.resync_point(tokens.SEMICOLON):
                declarations.append(self.declaration())
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
            # We could resync here after the comma.
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
        decls = self.declarations()
        
        # Body
        self.match(tokens.BEGIN)
        body = self.statements()
        self.match(tokens.END)
        self.match(tokens.PROCEDURE)
        
        return syntaxtree.ProcDecl(is_global, name, parameters, decls, body)
            
    def variable_declaration(self):
        is_global = self._consume_optional_token(tokens.GLOBAL)
        if self.token.type in (tokens.INT, tokens.FLOAT, tokens.BOOL, tokens.STRING_TYPE):
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
            with self.resync_point(tokens.SEMICOLON):
                statements.append(self.statement())
            self.match(tokens.SEMICOLON,
                       ParseError('Missing semicolon after statement',
                                  self.token._replace(start=self.token.end+1,
                                                      end=self.token.end+1)))
        return statements
    
    def statement(self):
        self.advance_token()
        # these calls can't all be inlined, since for_statement calls
        # assignment_statement specifically, and there's no reason to make that a
        # special case.
        if self.token.type == tokens.IF:
            return self.if_statement()
        if self.token.type == tokens.FOR:
            return self.for_statement()
        if self.token.type == tokens.RETURN:
            return tokens.RETURN
        if self.token.type == tokens.IDENTIFIER:
            if self.next_token.type == tokens.ASSIGN:
                return self.assignment_statement()
            if self.next_token.type == tokens.OPENPAREN:
                return self.procedure_call()
            if self.next_token.type == tokens.ERROR:
                raise ParseError(self.next_token.token, self.next_token)
        if self.token.type == tokens.ERROR:
            raise ParseError(self.token.token, self.token)
        raise ParseError('Invalid %r in statement' % self.token.token, self.token)
    
    def procedure_call(self):
        function_name = syntaxtree.Name(self.token.token)
        self.match(tokens.OPENPAREN)
        function_args = []
        if self.next_token.type != tokens.CLOSEPAREN:
            function_args.append(self.expression())
            while self.next_token.type == tokens.COMMA:
                self.advance_token()
                function_args.append(self.expression())
        self.match(tokens.CLOSEPAREN)
        return syntaxtree.Call(function_name, function_args)
    
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
        
        # At least one statement is required in the then clause.
        with self.resync_point(tokens.SEMICOLON):
            body = self.statements()
        if not body:
            raise ParseError('Missing body of if clause', self.token)
        
        if self.next_token.type == tokens.ELSE:
            self.advance_token()
            
            # One or more statements are required in the else clause as well.
            with self.resync_point(tokens.SEMICOLON):
                orelse = self.statements()
            if not orelse:
                raise ParseError('Missing body of else clause', self.token)
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
    import argparse

    def print_expression(node):
        if isinstance(node, syntaxtree.BinaryOp):
            print '(',
            print_expression(node.left)
            print node.op,
            print_expression(node.right)
            print ')',
        elif isinstance(node, syntaxtree.UnaryOp):
            print '(',
            print node.op,
            print_expression(node.operand)
            print ')',
        elif isinstance(node, syntaxtree.Num):
            print node.n,
        elif isinstance(node, syntaxtree.Name):
            print node.id,
        elif node == tokens.TRUE:
            print 'true',
        elif node == tokens.FALSE:
            print 'false',
        elif isinstance(node, syntaxtree.Subscript):
            print_expression(node.name),
            print '[',
            print_expression(node.index)
            print ']',
        elif isinstance(node, syntaxtree.Str):
            print node.s,
        else:
            print '?',

    argparser = argparse.ArgumentParser(description='Test the parser functionality. With the -e switch, treat the input as an expression to parse. Otherwise treat it as a filename to parse.')
    
    argparser.add_argument('filename_or_expression', help='the file to scan, or expression to test')
    argparser.add_argument('-e', '--expression', action='store_true', help='parse an expression directly (make sure to surround the expression in quotes)')
    args = argparser.parse_args()
    if args.expression:
        print_expression(_Parser(scanner.tokenize_string(args.filename_or_expression)).expression())
    else:
        try:
            print parse_tokens(scanner.tokenize_file(args.filename_or_expression))
        except ParseFailedError as err:
            print err
    
