'''Token constants.

This implementation isn't very DRY, but it's simple and works with code
completion. This is also similar to the method that the stdlib uses in
token.py.

The token types are assigned strings for readibility instead of the classic
arbitrary integer values. This is not a performance issue, because python
interns small strings, which allows equality comparisons to just use a pointer
compare, which is the same speed as an integer compare. '''

IDENTIFIER = 'IDENTIFIER'
STRING = 'STRING'
NUMBER = 'NUMBER'
COLON = 'COLON'
SEMICOLON = 'SEMICOLON'
COMMA = 'COMMA'
PLUS = 'PLUS'
MINUS = 'MINUS'
MULTIPLY = 'MULTIPLY'
DIVIDE = 'DIVIDE'
OPENPAREN = 'OPENPAREN'
CLOSEPAREN = 'CLOSEPAREN'
LT = 'LT'
LTE = 'LTE'
GT = 'GT'
GTE = 'GTE'
NOTEQUAL = 'NOTEQUAL'
EQUAL = 'EQUAL'
ASSIGN = 'ASSIGN'
OPENBRACE = 'OPENBRACE'
CLOSEBRACE = 'CLOSEBRACE'
STRING_KEYWORD = 'STRING_KEYWORD'
INT = 'INT'
BOOL = 'BOOL'
FLOAT = 'FLOAT'
GLOBAL = 'GLOBAL'
IN = 'IN'
OUT = 'OUT'
IF = 'IF'
THEN = 'THEN'
ELSE = 'ELSE'
CASE = 'CASE'
FOR = 'FOR'
AND = 'AND'
OR = 'OR'
NOT = 'NOT'
PROGRAM = 'PROGRAM'
PROCEDURE = 'PROCEDURE'
BEGIN = 'BEGIN'
RETURN = 'RETURN'
END = 'END'
EOF = 'EOF'