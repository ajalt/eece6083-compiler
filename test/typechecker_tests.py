import itertools

from nose.tools import raises

from ececompiler import scanner
from ececompiler import tokens
from ececompiler import parser
from ececompiler import syntaxtree as st
from ececompiler import typechecker
from ececompiler.typechecker import TypeCheckError

def get_parser(src):
    return parser.Parser(scanner.tokenize_string(src))

def check_valid_type(src, expected):
    ast = get_parser(src).expression()
    checker = typechecker.Checker()
    result = checker.get_type(ast)
    print result, expected
    assert not checker.error_encountered
    assert result == expected
    
@raises(TypeCheckError)
def check_invalid_type(src):
    ast = get_parser(src).expression()
    checker = typechecker.Checker()
    result = checker.get_type(ast)
    
def test_literal_types():
    for src, expected in (
        ('1', tokens.INT),
        ('1.0', tokens.FLOAT),
        ('"s"', tokens.STRING_TYPE),
        ('true', tokens.BOOL),
        ('false', tokens.BOOL),
    ):
        yield check_valid_type, src, expected
        
def test_undefined_identifiers():
    for src in ('x', 'x[0]'):
        yield check_invalid_type, src
        
def test_invalid_subscripts():
    for name in ('1', '1.0', '"s"', 'true', 'false', '(1 + 1)'):
        yield check_invalid_type, '%s[0]' % name

def check_valid_type_unification(left, right, expected):
    checker = typechecker.Checker()
    result = checker.unify_node_types(left, right)
    print 'Expected:', expected
    print 'Result:  ', result
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

@raises(TypeCheckError)
def check_invalid_type_unification(left, right):
    checker = typechecker.Checker()
    result = checker.unify_node_types(left, right)

def test_invalid_type_unifications():
    for left, right in (
        (st.Str('"s"'), st.Num('1')),
        (st.Str('"s"'), st.Num('1.0')),
    ):
        yield check_invalid_type_unification, left, right
        yield check_invalid_type_unification, right, left

def check_valid_expression(src):
    ast = get_parser(src).expression()
    checker = typechecker.Checker()
    checker.get_type(ast)
    assert not checker.error_encountered
    
@raises(TypeCheckError)
def check_invalid_expression(src):
    ast = get_parser(src).expression()
    checker = typechecker.Checker()
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
    yield check_valid_expression, 'not 1'
    yield check_valid_expression, '-1.0'
    
def test_chained_expression():
    check_valid_expression('1 + 2 + 3')
    
def test_valid_parenthesized_subexpressions():
    check_valid_expression('(1 + 1) * (1 + 1)')

def test_invalid_bitwise_operations():
    yield check_invalid_expression, '1.0 | 1.0'
    yield check_invalid_expression, '1.0 & 1.0'
    yield check_invalid_expression, 'not 1.0'

def test_invalid_binary_operations():
    for op in '+-/*|&':
        for left, right in itertools.permutations(('"string"', '"string"', '1'), 2):
            src = left + op + right
            yield check_invalid_expression, src
            
def check_node_type_annotation(src, node_type):
    ast = get_parser(src).expression()
    checker = typechecker.Checker()
    checker.get_type(ast)
    print 'Expected:', node_type
    print 'Got:     ', ast.node_type
    assert ast.node_type == node_type
    
def test_node_type_annotation():
    for src, node_type in (
        ('1 & 1', tokens.INT),
        ('1 | 1', tokens.INT),
        ('1 + 1', tokens.INT),
        ('1 - 1', tokens.INT),
        ('1 * 1', tokens.INT),
        ('1 / 1', tokens.INT),
        ('not 1', tokens.INT),
        ('1 + 1.0', tokens.FLOAT),
        ('1.0 + 1', tokens.FLOAT),
        ('1.0 + 1.0', tokens.FLOAT),
        ('true & 1', tokens.BOOL),
        ('1 & false', tokens.BOOL),
        ('true & false', tokens.BOOL),
        ('true | false', tokens.BOOL),
        ('not false', tokens.BOOL),
    ):
        yield check_node_type_annotation, src, node_type
            
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
        ('bool', 'true'),
        ('bool', 'false'),
        ('bool', '1'),
        ('int', '1'),
        ('int', '1.0'),
        ('float', '1.0'),
        ('float', '1'),
        ('string', '"s"'),
    ):
        yield check_program_is_valid, template % (type, arg)
        
def test_invalid_procedure_call_types():
    template = '''
    program test_program is
        procedure f (%s x in)
        
        begin end procedure;
    begin
        f(%s);
    end program
    '''
    for type, arg in (
        ('int', '"s"'),
        ('bool', '"s"'),
        ('float', '"s"'),
        ('string', '1'),
        ('string', '1.0'),
    ):
        yield check_program_is_invalid, template % (type, arg)
        
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
        
def test_valid_argument_to_out_parameter_in_procedure_call():
    src = '''
    program test_program is
        int x;
        procedure f (int y out)
        
        begin end procedure;
    begin
        f(x);
    end program
    '''
    yield check_program_is_valid, src
    
def test_invalid_argument_to_out_parameter_in_procedure_call():
    template = '''
    program test_program is
        procedure f (int y out)
        
        begin end procedure;
    begin
        f(%s);
    end program
    '''
    for arg in ('x', '1', '1.0', '"s"', 'true', 'false', '1 + 1'):
        yield check_program_is_invalid, template % arg
        
        
def test_recursive_procedure():
    src = '''
    program test_program is
        procedure f ()
            
        begin
            f();
        end procedure;
    begin
    end program
    '''
    yield check_program_is_valid, src
    
def test_call_to_undefined_function():
    src = '''
    program test_program is
        procedure f ()
        begin
            x();
        end procedure;
    begin
    end program
    '''
    yield check_program_is_invalid, src
    
def test_reference_to_global_variable():
    src = '''
    program test_program is
        global int x;
        procedure f ()
            
        begin
            x := 1;
        end procedure;
    begin
    end program
    '''
    yield check_program_is_valid, src
    
def test_reference_to_nonglobal_variable():
    src = '''
    program test_program is
        int x;
        procedure f ()
            
        begin
            x := 1;
        end procedure;
    begin
    end program
    '''
    yield check_program_is_invalid, src
    
def test_illegal_global_variable_in_procdecl():
    src = '''
    program test_program is
        procedure f ()
            global int x;
        begin
        end procedure;
    begin
    end program
    '''
    yield check_program_is_invalid, src
    
def test_assigning_to_out_parameter_in_procedure_body():
    src = '''
    program test_program is
        procedure f (int x out)
        begin
            x := 1;
        end procedure;
    begin
    end program
    '''
    yield check_program_is_valid, src
      
def test_reading_from_out_parameter_in_procedure_body():
    src = '''
    program test_program is
        procedure f (int x out)
        int y;
        begin
            y := x;
        end procedure;
    begin
    end program
    '''
    yield check_program_is_invalid, src
    
def test_assigning_to_in_parameter_in_procedure_body():
    src = '''
    program test_program is
        procedure f (int x in)
        begin
            x := 1;
        end procedure;
    begin
    end program
    '''
    yield check_program_is_invalid, src
      
def test_reading_from_in_parameter_in_procedure_body():
    src = '''
    program test_program is
        procedure f (int x in)
        int y;
        begin
            y := x;
        end procedure;
    begin
    end program
    '''
    yield check_program_is_valid, src  

def test_redefining_variable():
    src = '''
    program test_program is
        int x;
        float x;
    begin
    end program
    '''
    yield check_program_is_invalid, src
    
def test_redefining_parameter_with_parameter():
    src = '''
    program test_program is
        procedure f (int x in, float x in)
        begin
        end procedure;
    begin
    end program
    '''
    yield check_program_is_invalid, src
    
def test_redefining_parameter_with_variable():
    src = '''
    program test_program is
        procedure f (int x in)
            float x;
        begin
        end procedure;
    begin
    end program
    '''
    yield check_program_is_invalid, src
    
def test_shadowing_global_variable():
    src = '''
    program test_program is
        global int x;
        procedure f ()
            int x;
        begin
        end procedure;
    begin
    end program
    '''
    yield check_program_is_valid, src
    
def test_referencing_procedure_like_variable():
    src = '''
    program test_program is
        int x;
        procedure f ()
        begin
        end procedure;
    begin
        x := f;
    end program
    '''
    yield check_program_is_invalid, src
    
def test_two_invalid_types_in_expression():
    src = '''
    program test_program is
        int x;
    begin
        x := a + b;
    end program
    '''
    yield check_program_is_invalid, src
