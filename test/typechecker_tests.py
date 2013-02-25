import itertools

from nose.tools import raises

from src import scanner
from src import tokens
from src import parser
from src import syntaxtree as st
from src import typechecker

def get_parser(src):
    return parser._Parser(scanner.tokenize_string(src))

def check_valid_type(src, expected):
    ast = get_parser(src).expression()
    checker = typechecker._Checker()
    result = checker.get_type(ast)
    print result, expected
    assert not checker.error_encountered
    assert result == expected
    
def check_invalid_type(src):
    ast = get_parser(src).expression()
    checker = typechecker._Checker()
    result = checker.get_type(ast)
    assert checker.error_encountered
    
def test_literal_types():
    for src, expected in (
        ('1', tokens.INT),
        ('1.0', tokens.FLOAT),
        ('"s"', tokens.STRING_TYPE),
        ('true', tokens.INT),
        ('false', tokens.INT),
    ):
        yield check_valid_type, src, expected
        
def test_undefined_identifiers():
    for src in ('x', 'x[0]'):
        yield check_invalid_type, src

def check_valid_type_unification(left, right, expected):
    checker = typechecker._Checker()
    result = checker.unify_types(left, right)
    print result
    assert result == expected
    
def test_valid_type_unifications():
    for left, right, expected in (
        (st.Num('1'), st.Num('1'), tokens.INT),
        (st.Num('1.0'), st.Num('1'), tokens.FLOAT),
        (st.Num('1'), st.Num('1.0'), tokens.FLOAT),
        (st.Num('1.0'), st.Num('1.0'), tokens.FLOAT),
        (st.Str('"s"'), st.Str('"s"'), tokens.STRING_TYPE),
    ):
        yield check_valid_type_unification, left, right, expected

def test_invalid_type_unifications():
    for left, right in (
        (st.Str('"s"'), st.Num('1')),
        (st.Str('"s"'), st.Num('1.0')),
    ):
        yield check_valid_type_unification, left, right, None
        yield check_valid_type_unification, right, left, None

def check_valid_expression(src):
    ast = get_parser(src).expression()
    checker = typechecker._Checker()
    checker.get_type(ast)
    assert not checker.error_encountered
    
def check_invalid_expression(src):
    ast = get_parser(src).expression()
    checker = typechecker._Checker()
    checker.get_type(ast)
    assert checker.error_encountered
    
def test_valid_arithmetic_operatons():
    for op, lnum, rnum in itertools.product('+-*/', ('1', '1.0'), ('1', '1.0')):
        src = lnum + op + rnum
        yield check_valid_expression, src
        
def test_valid_bitwise_operatons():
    yield check_valid_expression, '1 | 1'
    yield check_valid_expression, '1 & 1'
    
def test_valid_unary_operations():
    yield check_valid_expression, '-1'
    yield check_valid_expression, '-1.0'
    
def test_chained_expression():
    check_valid_expression('1 + 2 + 3')
    
def test_valid_parenthesized_subexpressions():
    check_valid_expression('(1 + 1) * (1 + 1)')

def test_invalid_bitwise_operations():
    yield check_invalid_expression, '1.0 | 1.0'
    yield check_invalid_expression, '1.0 & 1.0'

def test_invalid_binary_operations():
    for op in '+-/*|&':
        for left, right in itertools.permutations(('"string"', '"string"', '1'), 2):
            src = left + op + right
            yield check_invalid_expression, src
            
def check_program_is_valid(src):
    ast = get_parser(src).parse()
    assert typechecker.tree_is_valid(ast)
    
def check_program_is_invalid(src):
    ast = get_parser(src).parse()
    assert not typechecker.tree_is_valid(ast)
    
def test_valid_declarations():
    template = '''
    program test_program is
        %s x%s;
    begin
        return;
    end program
    '''
    for type in ('string', 'int', 'float', 'bool'):
        for array_size in ('', '[1]'):
            yield check_program_is_valid, template % (type, array_size)
            
def test_invalid_array_declaration():
    src = '''
    program test_program is
        int x[1.0];
    begin
        return;
    end program
    '''
    check_program_is_invalid(src)
            
# There isn't any good way to isolate variable references as a separate unit, so
# we just have to test them as part of other tests.
def test_minimal_assignments():
    template = '''
    program test_program is
        %s x%s;
    begin
        x%s := %s;
    end program
    '''
    for type, val in (
        ('string', '"s"'),
        ('int', '1'),
        ('int', '1.0'),
        ('float', '1'),
        ('float', '1.0'),
        ('bool', 'true'),
        ('bool', 'false'),
        ('bool', '1'),
        ('bool', '0'),
    ):
        for array_size, array_subscript in (
            ('', ''),
            ('[1]', '[0]'),
        ):
            yield check_program_is_valid, template % (type, array_size, array_subscript, val)
            
def test_assignment_to_array_subscript():
    template = '''
    program test_program is
        int x[1];
    begin
        x[%s] := 1;
    end program
    '''
    for array_subscript in ('1', '1 + 2', 'x[0]'):
        yield check_program_is_valid, template % array_subscript
        
def test_assignment_to_invalid_array_subscript():
    template = '''
    program test_program is
        int x[1];
    begin
        x[%s] := 1;
    end program
    '''
    for array_subscript in ('1.0', '"s"', '1 + 1.0'):
        yield check_program_is_invalid, template % array_subscript
        
def test_valid_procedure_call_types():
    template = '''
    program test_program is
        procedure f (%s x in)
        
        begin end procedure;
    begin
        f(%s);
    end program
    '''
    for type, arg in (
        ('int', '1'),
        ('int', '1.0'),
        ('float', '1.0'),
        ('float', '1'),
        ('string', '"s"'),
    ):
        yield check_program_is_valid, template % (type, arg)
        
def test_multiple_prameters_in_procedure_call():
    template = '''
    program test_program is
        procedure f (%s)
        
        begin end procedure;
    begin
        f(%s);
    end program
    '''
    params = ('int a in', 'int b in', 'int c in')
    args = ('1', '2', '3')
    for i in xrange(len(params)):
        src = template % (', '.join(params[:i+1]), ', '.join(args[:i+1]))
    
