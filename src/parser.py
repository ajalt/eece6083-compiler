import itertools

import tokens
import scanner
import syntaxtree

def _report_error(msg, token):
    print 'Error on line %s: %s' % (token.lineno, msg)
    underline = '^' if token.start == token.end else '~'
    print '   ', token.line.rstrip()
    print '   ', ''.join((underline if token.start <= i <= token.end else ' ') for i in xrange(len(token.line.rstrip())))
    
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
                _report_error("Unexpected '%s'" % self.id, self.parser.token)
                raise SyntaxError
            
            def infix(self, left_term):
                _report_error("Unexpected '%s'" % self.id, self.parser.token)
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
            
        class TrueVal(Symbol):
            def __init__(self):
                pass
            
            def prefix(self):
                return syntaxtree.TrueVal
            
        class FalseVal(Symbol):
            def __init__(self):
                pass
            
            def prefix(self):
                return syntaxtree.FalseVal
            
        class InfixOperator(Symbol):
            def __init__(self, op, precedence):
                self.op = op
                self.precedence = precedence
                
            def infix(self, left_term):
                return syntaxtree.BinaryOp(self.op, left_term, self.parser.expression(self.precedence))
            
        class PrefixOperator(Symbol):
            def __init__(self, op, precedence):
                self.op = op
                self.precedence = precedence
                
            def prefix(self):
                return syntaxtree.UnaryOp(self.op, self.parser.expression(self.precedence))
            
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


        self.expression_operators = {
            tokens.NUMBER: Number,
            tokens.IDENTIFIER: Identifier,
            tokens.STRING: String,
            tokens.TRUE: TrueVal(),
            tokens.FALSE: FalseVal(),
            tokens.CLOSEPAREN: Symbol(tokens.CLOSEPAREN),
            tokens.COMMA: Symbol(tokens.COMMA),
            tokens.CLOSEBRACKET: Symbol(tokens.CLOSEBRACKET),
            tokens.OR: InfixOperator(tokens.OR, 1),
            tokens.AND: InfixOperator(tokens.AND, 2),
            tokens.NOT: PrefixOperator(tokens.NOT, 3),
            tokens.PLUS: InfixOperator(tokens.PLUS, 4),
            tokens.MINUS: Minus(4, 7),
            tokens.LT: InfixOperator(tokens.LT, 5),
            tokens.GTE: InfixOperator(tokens.GTE, 5),
            tokens.LTE: InfixOperator(tokens.LTE, 5),
            tokens.GT: InfixOperator(tokens.GT, 5),
            tokens.EQUAL: InfixOperator(tokens.EQUAL, 5),
            tokens.NOTEQUAL: InfixOperator(tokens.NOTEQUAL, 5),
            tokens.MULTIPLY: InfixOperator(tokens.MULTIPLY, 6),
            tokens.DIVIDE: InfixOperator(tokens.DIVIDE, 6),
            tokens.OPENPAREN: OpenParen(7),
            tokens.OPENBRACKET: OpenBracket(7),
            tokens.EOF: Symbol(tokens.EOF),
        }
                
    
    def _find_symbol(self, token):
        if token.type in (tokens.NUMBER, tokens.IDENTIFIER, tokens.STRING):
            return self.expression_operators[token.type](token.token)
        return self.expression_operators[token.type]
    
    @property
    def current_symbol(self):
        return self._find_symbol(self.token)
    
    @property
    def next_symbol(self):
        return self._find_symbol(self.next_token)
        
    def advance_token(self):
        self.token, self.next_token = next(self._token_iter)
        
    def match(self, token_type):
        if self.next_token.type != token_type:
            _report_error('Expected %r, found %r' % (token_type, self.next_token.type), self.next_token)
            raise SyntaxError
        self.advance_token()
    
    def parse(self):
        self.match(tokens.PROGRAM)
    
    def expression(self, precedence=0):
        self.advance_token()
        
        left_term = self.current_symbol.prefix()
        
        while precedence < self.next_symbol.precedence:
            self.advance_token()
            left_term = self.current_symbol.infix(left_term)
        
        return left_term


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
        
    parse = parse_tokens(scanner.tokenize_string(('a[]')))
    print parse
    print_node(parse)
    
