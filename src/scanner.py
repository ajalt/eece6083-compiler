'''Scan a string or file and generate language tokens.

tokenize_line and tokenize_file are both generators that generate tokens in the
form of tuples. Both functions generate namedtuples with the following members:

    the token type (a string, see tokens.py)
    the token/lexeme (a string)
    the starting position of the token in the line (an int)
    the ending position of the token in the line (an int)
    the number of the line in the file in which the token occurs (an int)
    the full original line (a string)

tokenize_line will always generate tokens with the line number member set to 0.
'''

import tokens
import collections

Token = collections.namedtuple('Token', ['type', 'token', 'start', 'end', 'lineno', 'line'])

token_map = {
    ':': tokens.COLON,
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
    '=': tokens.EQUAL,
    ':=': tokens.ASSIGN,
    '{': tokens.OPENBRACE,
    '}': tokens.CLOSEBRACE,
    'string': tokens.STRING_KEYWORD,
    'int': tokens.INT,
    'bool': tokens.BOOL,
    'float': tokens.FLOAT,
    'global': tokens.GLOBAL,
    'in': tokens.IN,
    'out': tokens.OUT,
    'if': tokens.IF,
    'then': tokens.THEN,
    'else': tokens.ELSE,
    'case': tokens.CASE,
    'for': tokens.FOR,
    'and': tokens.AND,
    'or': tokens.OR,
    'not': tokens.NOT,
    'program': tokens.PROGRAM,
    'procedure': tokens.PROCEDURE,
    'begin': tokens.BEGIN,
    'return': tokens.RETURN,
    'end': tokens.END,
}

def tokenize_line(line):
    '''Generate tokens from a single line of text.
    
    The generator produces 6-tuples with the following members:
    
        the token type (a string, see tokens.py)
        the token/lexeme (a string)
        the starting position of the token in the line (an int)
        the ending position of the token in the line (an int)
        the integer 0
        the full original line (a string)
    '''
    pos = 0
    length = len(line)
    
    while pos < length:
        c = line[pos]
        if line[pos:pos+2] == '//': # comment
            return
        if c.isspace(): # whitespace
            pass
        elif c in ';,+-*/()={}': # unambiguous terminals
            yield Token(token_map[c], c, pos, pos, 0, line)
        elif c in '<>:': # ambiguous terminals
            try:
                lexeme = line[pos:pos+2]
                yield Token(token_map[lexeme], lexeme, pos, pos + len(lexeme) - 1, 0, line)
                pos += 1
            except KeyError:
                yield Token(token_map[c], c, pos, pos, 0, line)
        elif c == '!': # NOTEQUAL
            if line[pos:pos+2] == '!=':
                yield Token(tokens.NOTEQUAL, '!=', pos, pos + 1, 0, line)
                pos += 1
            else:
                raise SyntaxError("Illegal character '%s' encountered at column %s" % (line[pos+1], pos+1))
        elif c.isalpha(): # identifiers
            startpos = pos
            pos = _advance_pos(line, pos, lambda c:c.isalnum()) # \w*
            token_type = token_map.get(line[startpos:pos], tokens.IDENTIFIER)
            yield Token(token_type, line[startpos:pos], startpos, pos - 1, 0, line)
            pos -= 1
        elif c.isdigit(): # number
            startpos = pos
            pos = _advance_pos(line, pos, lambda c:c.isdigit()) # [0-9_]*
            if pos < length and line[pos] == '.': 
                pos = _advance_pos(line, pos + 1, lambda c:c.isdigit()) # [0-9_]*
            yield Token(tokens.NUMBER, line[startpos:pos], startpos, pos - 1, 0, line)
            pos -= 1
        elif c == '"': # string
            startpos = pos
            pos = line.find('"', pos + 1)
            if pos == -1:
                raise SyntaxError('EOL while scanning string literal')
            # use [startpos:pos+1] to include the final quotation mark
            yield Token(tokens.STRING, line[startpos:pos+1], startpos, pos, 0, line)
        else:
            raise SyntaxError("Illegal character '%s' encountered at column %s" % (c, pos))
        pos += 1
    
def tokenize_file(filename):
    '''Generate tokens from a file on disk.
    
    The generator produces 6-tuples with the following members:
    
        the token type (a string, see tokens.py)
        the token/lexeme (a string)
        the starting position of the token in the line (an int)
        the ending position of the token in the line (an int)
        the number of the line in the file in which the token occurs (an int)
        the full original line (a string)
    '''
    with open(filename) as file:
        for lineno, line in enumerate(file):
            try:
                for token in tokenize_line(line):
                    yield token._replace(lineno=lineno)
            except SyntaxError, err:
                print 'Line', lineno, ':', err
                
    # We probably don't need and EOF token at all, so this might get removed later.
    # Use the fact that python 2.x leaks index variables outside of their loop's scope to get lineno.
    yield Token(tokens.EOF, '', 0, 0, lineno + 1, '')
    
    
def _advance_pos(line, pos, test):
    while pos < len(line) and (line[pos]  == '_' or test(line[pos])):
        pos += 1
    return pos
    
    
if __name__ == '__main__':
    for token in tokenize_line('string s = 123_.; global in "q2__" :<=<!==::={}>>=2_2._2'):
        print token[:-1]