import itertools

import tokens
import scanner

class _Parser(object):
    def __index__(self, tokens):
        # tee will take care of caching the iterator so that we can get the lookahead
        self.token, self.next_token = itertools.tee(tokens)
        next(next_token)
        
        # this will iterate over both of the iterator returned by tee in parallel
        # next_token will be None when token is the last token in the stream
        self._token_iter = itertools.izip_longest(token, next_token)
            
    def _advance_token(self):
        self.token, self.next_token = next(self._token_iter)
    
    def program():
        pass
    
    def program_header():
        pass
    
    def program_body():
        pass
    
    def declaration():
        pass
    
    def procedure_declaration():
        pass
    
    def procedure_header():
        pass
    
    def parameter_list():
        pass
    
    def parameter():
        pass
    
    def procedure_body():
        pass
    
    def variable_declaration():
        pass
    
    def type_mark():
        pass
    
    def array_size():
        pass
    
    def statement():
        pass
    
    def procedure_call():
        pass
    
    def assignment_statement():
        pass
    
    def destination():
        pass
    
    def if_statement():
        pass
    
    def loop_statement():
        pass
    
    def return_statement():
        pass
    
    def expression():
        pass
    
    def arith_op():
        pass
    
    def arith_op2():
        pass
    
    def relation():
        pass
    
    def relation2():
        pass
    
    def term():
        pass
    
    def term2():
        pass
    
    def factor():
        pass
    
    def name():
        pass
    
    def argument_list():
        pass


def parse_file(filename):
    return parse_tokens(scanner.tokenize_file(filename))

def parse_line(line):
    return parse_tokens(scanner.tokenize_line(line))

def parse_tokens(tokens):
    pass
    
    
if __name__ == '__main__':
    parse_tokens((1,2,3,4))