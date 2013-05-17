'''Scan a string or file and generate language tokens.

Functions tokenize_string and tokenize_file are both generators that generate
namedtuples with the following members:

    the token type (a string, see tokens.py)
    the token/lexeme (a string)
    the starting position of the token in the line (an int)
    the ending position of the token in the line (an int)
    the number of the line in the file in which the token occurs (an int)
    the full original line (a string)

Scanning does not stop when a syntax error is encountered. Instead, errors are
reported by yielding a token of type ERROR. In these tokens, the token string is
the error message, and the start and end indices are the locations of the error.
'''

import collections
import string
import StringIO

import tokens

Token = collections.namedtuple('Token', ['type', 'token', 'start', 'end', 'lineno', 'line'])

legal_string_characters = string.letters + string.digits + " _,;:.'"

token_map = {
    ';': tokens.SEMICOLON,
    ',': tokens.COMMA,
    '+': tokens.PLUS,
    '-': tokens.MINUS,
    '*': tokens.MULTIPLY,
    '/': tokens.DIVIDE,
    '(': tokens.OPENPAREN,
    ')': tokens.CLOSEPAREN,
    '<': tokens.LT,
    '<=': tokens.LTE,
    '>': tokens.GT,
    '>=': tokens.GTE,
    '!=': tokens.NOTEQUAL,
    '==': tokens.EQUAL,
    ':=': tokens.ASSIGN,
    '[': tokens.OPENBRACKET,
    ']': tokens.CLOSEBRACKET,
    '&': tokens.AND,
    '|': tokens.OR,
    'string': tokens.STRING_TYPE,
    'int': tokens.INT,
    'bool': tokens.BOOL,
    'float': tokens.FLOAT,
    'global': tokens.GLOBAL,
    'in': tokens.IN,
    'out': tokens.OUT,
    'if': tokens.IF,
    'then': tokens.THEN,
    'else': tokens.ELSE,
    'for': tokens.FOR,
    'not': tokens.NOT,
    'program': tokens.PROGRAM,
    'procedure': tokens.PROCEDURE,
    'begin': tokens.BEGIN,
    'return': tokens.RETURN,
    'end': tokens.END,
    'true': tokens.TRUE,
    'false': tokens.FALSE,
    'is': tokens.IS
}

def _advance_pos(line, pos, test):
    # Return the index of the first character that fails the test function and is not '_'
    while pos < len(line) and (line[pos]  == '_' or test(line[pos])):
        pos += 1
    return pos

def _tokenize_line(line, lineno=0):
    pos = 0
    length = len(line)
    
    while pos < length:
        c = line[pos]
        if line[pos:pos+2] == '//': # comment
            return
        if c.isspace(): # whitespace
            pass
        elif c in ';,+-*/(){}[]&|': # single character lexemes
            yield Token(token_map[c], c, pos, pos, lineno, line)
        elif c in '<>!=:': # ambiguous and two character lexemes
            try:
                lexeme = line[pos:pos+2]
                yield Token(token_map[lexeme], lexeme, pos, pos + len(lexeme) - 1, lineno, line)
                pos += 1
            except KeyError:
                if c in '<>':
                    yield Token(token_map[c], c, pos, pos, lineno, line)
                else:
                    yield Token(tokens.ERROR, "Illegal character '%s' encountered" % line[pos], pos, pos, lineno, line)
        elif c.isalpha(): # identifiers
            startpos = pos
            pos = _advance_pos(line, pos, lambda c:c.isalnum()) # \w*
            token_type = token_map.get(line[startpos:pos], tokens.IDENTIFIER)
            yield Token(token_type, line[startpos:pos], startpos, pos - 1, lineno, line)
            pos -= 1
        elif c.isdigit(): # number
            startpos = pos
            pos = _advance_pos(line, pos, lambda c:c.isdigit()) # [0-9_]*
            if pos < length and line[pos] == '.': 
                pos = _advance_pos(line, pos + 1, lambda c:c.isdigit()) # [0-9_]*
            # We remove underscore characters from numbers here with replace().
            yield Token(tokens.NUMBER, line[startpos:pos].replace('_', ''), startpos, pos - 1, lineno, line)
            pos -= 1
        elif c == '"': # string
            startpos = pos
            pos = line.find('"', pos + 1)
            if pos == -1:
                yield Token(tokens.ERROR, 'EOL while scanning string literal', startpos, length-1, lineno, line)
                return
            # use [startpos:pos+1] to include the final quotation mark
            lexeme = line[startpos:pos+1]
            illegal_characters = [(i, c) for (i, c) in enumerate(lexeme[1:-1]) if c not in legal_string_characters]
            if illegal_characters:
                yield Token(tokens.ERROR, 'Illegal characters %s found in string' % str(tuple(c for i, c in illegal_characters)), startpos, pos, lineno, line)
            else:
                yield Token(tokens.STRING, lexeme, startpos, pos, lineno, line)
        else:
            yield Token(tokens.ERROR, "Illegal character '%s' encountered" % c, pos, pos, lineno, line)
        pos += 1
        
def _tokenize_file_obj(file_):
    lineno = 1
    for lineno, line in enumerate(file_, 1):
        for token in _tokenize_line(line, lineno):
            yield token
    yield Token(tokens.EOF, 'EOF', 0, 0, lineno, '')
    
def tokenize_string(string_):
    '''Generate tokens from a multiline string.
    
    The generator produces 6-tuples with the following members:
    
        the token type (a string, see tokens.py)
        the token/lexeme (a string)
        the starting position of the token in the line (an int)
        the ending position of the token in the line (an int)
        the number of the line in the file in which the token occurs (an int)
        the full original line (a string)
        
    The final token generated will be 'EOF'
    '''
    return _tokenize_file_obj(StringIO.StringIO(string_))
        
    
def tokenize_file(filename):
    '''Generate tokens from a file on disk.
    
    The generator produces 6-tuples with the following members:
    
        the token type (a string, see tokens.py)
        the token/lexeme (a string)
        the starting position of the token in the line (an int)
        the ending position of the token in the line (an int)
        the number of the line in the file in which the token occurs (an int)
        the full original line (a string)

    The final token generated will be 'EOF'
    '''
    with open(filename) as file:
        # We can't just return the generator created in _tokenize_file_obj here,
        # because the file will close as soon as we do. It will remain open if
        # this function is also a generator.
        for token in _tokenize_file_obj(file):
            yield token
            
if __name__ == '__main__':
    import argparse
    
    argparser = argparse.ArgumentParser(description='Test the scanner functionality')
    argparser.add_argument('filename', help='the file to scan')
    args = argparser.parse_args()
    
    for token in tokenize_file(args.filename):
        if token.type == tokens.ERROR:
            print token.token
            print '   ', token.line.rstrip()
            print '   ', ''.join(('^' if token.start <= i <= token.end else ' ') for i in xrange(len(token.line)))
            print
        else:
            print token
