import tokens

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
    'string': tokens.STRING,
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
    pos = 0
    length = len(line)
    
    while pos < length:
        c = line[pos]
        if c == '/' and pos < length - 1 and line[pos + 1] == '/': # comment
            return
        if c in ' \t': # whitespace
            pass
        elif c in ';,+-*/()={}': # unambiguous terminals
            yield c, token_map[c]
        elif c in '<>:': # ambiguous terminals
            try:
                yield line[pos:pos+2], token_map[line[pos:pos+2]]
                pos += 1
            except KeyError:
                yield c, token_map[c]
        elif c == '!': # NOTEQUAL
            if pos < length - 1 and line[pos + 1] == '=':
                yield '!=', tokens.NOTEQUAL
            else:
                raise SyntaxError("Illegal character '%s' encountered at column %s" % (c, pos))
        elif c.isalpha(): # identifiers
            startpos = pos
            while line[pos] == '_' or line[pos].isalnum(): # \w*
                pos += 1
            token_type = token_map.get(line[startpos:pos], tokens.IDENTIFIER)
            yield line[startpos:pos], token_type
            pos -= 1
        elif c.isdigit(): # number
            startpos = pos
            while line[pos] == '_' or line[pos].isdigit(): # [0-9_]*
                pos += 1
            if line[pos] == '.': 
                pos += 1
                while line[pos] == '_' or line[pos].isdigit(): # [0-9_]*
                    pos += 1
            yield line[startpos:pos], tokens.NUMBER
            pos -= 1
        elif c == '"': # string
            startpos = pos
            pos = line.find('"', pos + 1)
            if pos == -1:
                raise SyntaxError('EOL while scanning string literal')
            # use [startpos:pos+1] to include the final quotation mark
            yield line[startpos:pos+1], tokens.STRING
        else:
            raise SyntaxError("Illegal character '%s' encountered at column %s" % (c, pos))
        pos += 1
    
def tokenize_file(filename):
    with open(filename) as file:
        for lineno, line in enumerate(file):
            try:
                for token in tokenize_line(line):
                    yield token
            except SyntaxError, err:
                print 'Line', lineno, ':', err
    yield '', tokens.EOF
    
    
if __name__ == '__main__':
    print list(tokenize_line('string s = 123_.; global in "q2__" :<=<!==::={}>>='))