grammar antlrGrammar;

AND: '&';
THEN: 'then';
BEGIN: 'begin';
FLOAT: 'float';
RETURN: 'return';
GTE: '>=';
INTEGER: 'int';
LTE: '<=';
ELSE: 'else';
GLOBAL: 'global';
ASSIGN: ':=';
OUT: 'out';
IF: 'if';
IN: 'in';
NOT: 'not';
FALSE: 'false';
NOTEQUAL: '!=';
OPENBRACE: '{';
STRING: 'string';
CASE: 'case';
END: 'end';
FOR: 'for';
CLOSEPAREN: ')';
OPENPAREN: '(';
OPENBRACKET: '[';
CLOSEBRACKET: ']';
PLUS: '+';
MULTIPLY: '*';
MINUS: '-';
COMMA: ',';
DIVIDE: '/';
OR: '|';
TRUE: 'true';
PROGRAM: 'program';
BOOL: 'bool';
CLOSEBRACE: '}';
SEMICOLON: ';';
COLON: ':';
EQUAL: '==';
LT: '<';
PROCEDURE: 'procedure';
GT: '>';
IS: 'is';
NUMBER : [0-9][0-9_]*[.[0-9_]*];
STRING_LITERAL : '"'[A-Za-z0-9 _,;:.']*'"';
IDENTIFIER : [A-Za-z][A-Za-z0-9_]*;

program 
    :program_header program_body
    ;

program_header 
    :PROGRAM IDENTIFIER IS
    ;

program_body 
    :( declaration SEMICOLON )*
      BEGIN
          ( statement SEMICOLON )*
      END PROGRAM
    ;

procedure_declaration 
    :procedure_header procedure_body
    ;

procedure_header 
    :PROCEDURE IDENTIFIER OPENPAREN parameter_list? CLOSEPAREN
    ;

parameter_list 
    :parameter COMMA parameter_list
    |parameter
    ;

parameter 
    :variable_declaration IN 
    |variable_declaration OUT
    ;

procedure_body 
    :( declaration SEMICOLON )*
    BEGIN
        ( statement SEMICOLON )*
    END PROCEDURE
    ;

declaration 
    :GLOBAL? procedure_declaration
    |GLOBAL? variable_declaration
    ;

variable_declaration 
    :type_mark IDENTIFIER (OPENBRACKET array_size CLOSEBRACKET)?
    ;

type_mark 
    :INTEGER
    |FLOAT
    |BOOL
    |STRING
    ;

array_size 
    :NUMBER
    ;

statement 
    :assignment_statement
    |if_statement
    |loop_statement
    |return_statement
    |procedure_call
    ;

procedure_call 
    :IDENTIFIER OPENPAREN argument_list? CLOSEPAREN
    ;

assignment_statement 
    :destination ASSIGN expression
    ;

destination 
    :IDENTIFIER (OPENBRACE expression CLOSEBRACE)?
    ;

if_statement 
    :IF OPENPAREN expression CLOSEPAREN THEN ( statement SEMICOLON )+
    (ELSE ( statement SEMICOLON )+)?
    END IF
    ;

loop_statement 
    :FOR OPENPAREN assignment_statement SEMICOLON expression CLOSEPAREN
    ( statement SEMICOLON )*
    END FOR
    ;

return_statement 
    :RETURN
    ;

expression
    :NOT? arith_op expression2
    ;

expression2
    :AND arith_op expression2
    |OR arith_op expression2
    |
    ;

arith_op
    :relation arith_op2
    ;

arith_op2
    :PLUS relation arith_op2
    |MINUS relation arith_op2
    |
    ;
   
relation
    :term relation2
    ;

relation2
    :compare_op term relation2
    |
    ;

compare_op
    : (LT | GTE | LTE | GT | EQUAL | NOTEQUAL )
    ;

term
    :factor term2
    ;

term2
    :MULTIPLY factor term2
    |DIVIDE factor term2
    |
    ;

factor 
    :OPENPAREN expression CLOSEPAREN
    |MINUS? name
    |MINUS? NUMBER
    |( STRING_LITERAL | TRUE | FALSE )
    ;

name 
    :IDENTIFIER ( OPENBRACKET expression CLOSEBRACKET )?
    ;

argument_list 
    :expression COMMA argument_list
    |expression
    ;


