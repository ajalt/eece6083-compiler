import itertools

import tokens
import scanner
import syntaxtree

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
                raise SyntaxError
            
            def infix(self, left_term):
                raise SyntaxError
            
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
            
        class InfixOperator(Symbol):
            def __init__(self, op, precedence):
                self.op = op
                self.precedence = precedence
                
            def infix(self, left_term):
                return syntaxtree.BinaryOp(self.op, left_term, self.parser.expression(self.precedence))
            
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
                    while self.parser.token.type == tokens.COMMA:
                        self.parser.match(tokens.COMMA)
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


        self.expression_operators = {
            tokens.NUMBER: Number,
            tokens.IDENTIFIER: Identifier,
            tokens.STRING: String,
            tokens.CLOSEPAREN: Symbol(tokens.CLOSEPAREN),
            tokens.COMMA: Symbol(tokens.COMMA),
            tokens.CLOSEBRACKET: Symbol(tokens.CLOSEBRACKET),
            tokens.PLUS: InfixOperator(tokens.PLUS, 1),
            tokens.MINUS: Minus(1, 4),
            tokens.LT: InfixOperator(tokens.LT, 2),
            tokens.GTE: InfixOperator(tokens.GTE, 2),
            tokens.LTE: InfixOperator(tokens.LTE, 2),
            tokens.GT: InfixOperator(tokens.GT, 2),
            tokens.EQUAL: InfixOperator(tokens.EQUAL, 2),
            tokens.NOTEQUAL: InfixOperator(tokens.NOTEQUAL, 2),
            tokens.MULTIPLY: InfixOperator(tokens.MULTIPLY, 3),
            tokens.DIVIDE: InfixOperator(tokens.DIVIDE, 3),
            tokens.OPENPAREN: OpenParen(4),
            tokens.OPENBRACKET: OpenBracket(4),
            tokens.EOF: Symbol(tokens.EOF),
        }
                
    
    @property
    def current_symbol(self):
        if self.token.type in (tokens.NUMBER, tokens.IDENTIFIER, tokens.STRING):
            return self.expression_operators[self.token.type](self.token.token)
        return self.expression_operators[self.token.type]
    
    @property
    def next_symbol(self):
        if self.next_token.type in (tokens.NUMBER, tokens.IDENTIFIER):
            return self.expression_operators[self.next_token.type](self.next_token.token)
        return self.expression_operators[self.next_token.type]
        
    def advance_token(self):
        self.token, self.next_token = next(self._token_iter)
        
    def match(self, token_type):
        if self.next_token.type != token_type:
            raise SyntaxError('Expected %r, found %r' % (token_type, self.token.token))
        self.advance_token()
    
    def parse(self):
        return self.expression(0)
    
    def expression(self, precedence=0):
        self.advance_token()
        
        left_term = self.current_symbol.prefix()
        
        while precedence < self.next_symbol.precedence:
            self.advance_token()
            left_term = self.current_symbol.infix(left_term)
        
        return left_term


def parse_file(filename):
    return parse_tokens(scanner.tokenize_file(filename))

def parse_line(line):
    return parse_tokens(scanner.tokenize_string(line))

def parse_tokens(token_stream):
    return _Parser(token_stream).parse()
    
    
if __name__ == '__main__':
    
    def print_node(node):
        if isinstance(node, syntaxtree.BinaryOp):
            print '(',
            print_node(node.left)
            print node.op,
            print_node(node.right)
            print ')',
        elif isinstance(node, syntaxtree.Num):
            print node.n,
        elif isinstance(node, syntaxtree.Name):
            print node.id,
        elif isinstance(node, syntaxtree.Call):
            print '%s(' % node.func.id,
            for arg in node.args:
                print_node(arg)
                print ',',
            print ')',
        
    parse = parse_line('func()')
    print parse
    print_node(parse)
    
