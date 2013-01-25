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

Scanning does not stop when a syntax error is encountered. Instead, errors are
reported by yielding a token of type ERROR. In these tokens, the token string is
the error message, and the start and end indices are the locations of the error.
'''

import collections
import string

import tokens

Token = collections.namedtuple('Token', ['type', 'token', 'start', 'end', 'lineno', 'line'])

legal_string_characters = string.letters + string.digits + " _,;:.'"

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
    'true': tokens.TRUE,
    'false': tokens.FALSE,
}

def tokenize_line(line, lineno=0):
    '''Generate tokens from a single line of text.
    
    The generator produces 6-tuples with the following members:
    
        the token type (a string, see tokens.py)
        the token/lexeme (a string)
        the starting position of the token in the line (an int)
        the ending position of the token in the line (an int)
        the number of the line in the file in which the token occurs (an int, default=0)
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
            yield Token(token_map[c], c, pos, pos, lineno, line)
        elif c in '<>:': # ambiguous terminals
            try:
                lexeme = line[pos:pos+2]
                yield Token(token_map[lexeme], lexeme, pos, pos + len(lexeme) - 1, lineno, line)
                pos += 1
            except KeyError:
                yield Token(token_map[c], c, pos, pos, lineno, line)
        elif c == '!': # NOTEQUAL
            if line[pos:pos+2] == '!=':
                yield Token(tokens.NOTEQUAL, '!=', pos, pos + 1, lineno, line)
                pos += 1
            else:
                # If we're at the end of a line, the exclamation point itself is
                # illegal, otherwise the character after it is illegal.
                errorpos = pos if pos == length - 1 else pos + 1
                yield Token(tokens.ERROR, "Illegal character '%s' encountered" % line[errorpos], errorpos, errorpos, lineno, line)
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
            yield Token(tokens.NUMBER, line[startpos:pos], startpos, pos - 1, lineno, line)
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
            for token in tokenize_line(line, lineno):
                yield token
                
    
def _advance_pos(line, pos, test):
    # Return the index of the first character that fails the test function
    while pos < len(line) and (line[pos]  == '_' or test(line[pos])):
        pos += 1
    return pos

    
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
    