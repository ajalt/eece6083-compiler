from nose.tools import raises

import string
import os
import itertools

from src import scanner
from src import tokens
from src import parser
from src import syntaxtree as st

def get_parser(src):
    return parser._Parser(scanner.tokenize_string(src))

# expression tests
def parse_ex(exp):
    return get_parser(exp).expression()

def test_number():
    ast = parse_ex('123')
    # We have to test instance type seperately, since == only does tuple compare
    assert isinstance(ast, st.Num)
    assert ast == st.Num('123')

def test_name():
    ast = parse_ex('name')
    assert isinstance(ast, st.Name)
    assert ast == st.Name('name')

def test_str():
    ast = parse_ex('"str"')
    assert isinstance(ast, st.Str)
    assert ast == st.Str('"str"')

def test_literal_true():
    assert parse_ex('true') == st.Num('1')

def test_literal_false():
    assert parse_ex('false') == st.Num('0')

def test_unary_minus():
    ast = parse_ex('-1')
    assert isinstance(ast, st.UnaryOp)
    assert ast == st.UnaryOp(tokens.MINUS, st.Num('1'))

def test_unary_not():
    ast = parse_ex('not 1')
    assert isinstance(ast, st.UnaryOp)
    assert ast == st.UnaryOp(tokens.NOT, st.Num('1'))

def test_binary_ops():
    ops = {
        '&': tokens.AND,
        '|': tokens.OR,
        '+': tokens.PLUS,
        '-': tokens.MINUS,
        '*': tokens.MULTIPLY,
        '/': tokens.DIVIDE,
        '<': tokens.LT,
        '<=': tokens.LTE,
        '>': tokens.GT,
        '>=': tokens.GTE,
        '!=': tokens.NOTEQUAL,
        '==': tokens.EQUAL,
    }

    for op, tok in ops.iteritems():
        yield check_binary_op, op, tok
        yield check_unmatched_binary_op, op

def check_binary_op(op, tok):
    ast = parse_ex('1 %s 2' % op)
    assert isinstance(ast, st.BinaryOp)
    assert ast == st.BinaryOp(tok, st.Num('1'), st.Num('2'))

@raises(parser.ParseError)
def check_unmatched_binary_op(op):
    parse_ex('1 %s' % op)

@raises(parser.ParseError)
def test_missing_operand():
    print parse_ex('1 + + 4')

def test_parenthesis_equal_containing_expression():
    exp = '1 + 2'
    expected = parse_ex(exp)
    got = parse_ex('(%s)' % exp)
    print 'Expected:', expected
    print 'Got:     ', got
    assert expected == got

def test_parenthesis_grouping():
    assert parse_ex('2 * (1 + 3)') == st.BinaryOp(tokens.MULTIPLY, st.Num('2'),
                                st.BinaryOp(tokens.PLUS, st.Num('1'), st.Num('3')))

@raises(parser.ParseError)
def test_unmatched_parentesis():
    parse_ex('1 + (')

@raises(parser.ParseError)
def test_empty_parenthesis():
    parse_ex('()')

def test_subscript():
    ast = parse_ex('a[1]')
    print ast
    assert isinstance(ast, st.Subscript)
    assert ast == st.Subscript(st.Name('a'), st.Num('1'))

@raises(parser.ParseError)
def test_empty_subsrcipt():
    parse_ex('a[]')

@raises(parser.ParseError)
def test_unmatched_bracket():
    parse_ex('a[')


# declaration tests

def parse_decl(src):
    return get_parser(src).declaration()

# variable declartaion tests
def test_type_decls():
    types = {
        'string': tokens.STRING_TYPE,
        'int': tokens.INT,
        'bool': tokens.BOOL,
        'float': tokens.FLOAT,
    }
    for name, tok in types.iteritems():
        for is_global in (True, False):
            for array_len in (None, '0', '1'):
                yield check_type_declaration, is_global, name, tok, array_len

def check_type_declaration(is_global, name, tok, array_len):
    ast = parse_decl('%s %s x%s' %
                     ('global' if is_global else '',
                      name,
                      '[%s]' % array_len if array_len is not None else ''))
    array_len_node = None if array_len is None else st.Num(array_len)
    expected = st.VarDecl(is_global, tok, st.Name('x'), array_len_node)
    print 'Expected:', expected
    print 'Got:     ', ast
    assert isinstance(ast, st.VarDecl)
    assert ast == expected

@raises(parser.ParseError)
def test_double_global():
    parse_decl('global global int x')

@raises(parser.ParseError)
def test_empty_brackets():
    parse_decl('int x[]')

@raises(parser.ParseError)
def test_expr_in_array_decl():
    parse_decl('int x[1 + 2]')

@raises(parser.ParseError)
def test_variable_arary_decl():
    parse_decl('int x[g]')

@raises(parser.ParseError)
def test_missing_type_mark():
    parse_decl('global x')

@raises(parser.ParseError)
def test_missing_name():
    parse_decl('int')

# procedure declaration tests

def check_procedure_declaraiton(src, expected):
    ast = parse_decl(src)
    print 'Got:     ', ast
    print 'Expected:', expected

    assert isinstance(ast, st.ProcDecl)
    assert isinstance(ast.name, st.Name)
    assert isinstance(ast.params, list)
    assert isinstance(ast.decls, list)
    assert isinstance(ast.body, list)
    assert ast == expected

def test_minimal_procecure_declaration():
    src = 'procedure f() begin end procedure'
    expected = st.ProcDecl(False, st.Name('f'), [], [], [])
    check_procedure_declaraiton(src, expected)

def test_global_procedure():
    src = 'global procedure f() begin end procedure'
    expected = st.ProcDecl(True, st.Name('f'), [], [], [])
    check_procedure_declaraiton(src, expected)

def test_one_variable_declaration_in_procedure_declaration():
    src = 'procedure f() int x; begin end procedure'
    expected = st.ProcDecl(False, st.Name('f'), [],
                           [st.VarDecl(False, tokens.INT, st.Name('x'), None)], [])
    check_procedure_declaraiton(src, expected)

def test_two_variable_declarations_in_procedure_declaration():
    src = 'procedure f() int x; int y; begin end procedure'
    expected = st.ProcDecl(False, st.Name('f'), [],
                           [st.VarDecl(False, tokens.INT, st.Name('x'), None),
                            st.VarDecl(False, tokens.INT, st.Name('y'), None)], [])
    check_procedure_declaraiton(src, expected)

def test_procecure_declaration_with_one_in_parameter():
    src = 'procedure f(int x in) begin end procedure'
    expected = st.ProcDecl(False, st.Name('f'),
        [st.Param(st.VarDecl(False, tokens.INT, st.Name('x'), None), tokens.IN)], [], [])
    check_procedure_declaraiton(src, expected)

def test_procecure_declaration_with_one_out_parameter():
    src = 'procedure f(int x out) begin end procedure'
    expected = st.ProcDecl(False, st.Name('f'),
        [st.Param(st.VarDecl(False, tokens.INT, st.Name('x'), None), tokens.OUT)], [], [])
    check_procedure_declaraiton(src, expected)

def test_procecure_declaration_with_two_parameters():
    src = 'procedure f(int x in, int y out) begin end procedure'
    expected = st.ProcDecl(False, st.Name('f'),
        [st.Param(st.VarDecl(False, tokens.INT, st.Name('x'), None), tokens.IN),
         st.Param(st.VarDecl(False, tokens.INT, st.Name('y'), None), tokens.OUT)], [], [])
    check_procedure_declaraiton(src, expected)

def test_one_statement_in_procedure_declaration():
    src = 'procedure f() begin return; end procedure'
    expected = st.ProcDecl(False, st.Name('f'), [], [], [tokens.RETURN])
    check_procedure_declaraiton(src, expected)

def test_two_statements_in_procedure_declaration():
    src = 'procedure f() begin return; return; end procedure'
    expected = st.ProcDecl(False, st.Name('f'), [], [], [tokens.RETURN, tokens.RETURN])
    check_procedure_declaraiton(src, expected)

@raises(parser.ParseError)
def test_missing_first_procedure_keyword():
    parse_decl('f() begin end procedure')

@raises(parser.ParseError)
def test_missing_begin_keyword():
    parse_decl('procedure f() end procedure')

@raises(parser.ParseError)
def test_missing_end_keyword():
    parse_decl('procedure f() begin procedure')

@raises(parser.ParseError)
def test_missing_final_procedure_keyword():
    parse_decl('procedure f() begin end')

@raises(parser.ParseError)
def test_missing_paremeter_direction():
    parse_decl('procedure f(int x) begin end procedure')

@raises(parser.ParseError)
def test_missing_open_paren():
    parse_decl('procedure f) begin end procedure')

@raises(parser.ParseError)
def test_missing_close_paren():
    parse_decl('procedure f( begin end procedure')

@raises(parser.ParseError)
def test_trailing_comma_in_parameter_list():
    parse_decl('procedure f(int x in,) begin end procedure')

@raises(parser.ParseError)
def test_missing_comma_in_paremeter_list():
    parse_decl('procedure f(int x in int y out) begin end procedure')


# statement tests

def parse_statement(src):
    return get_parser(src).statement()

# assignment
def test_assignment_statement():
    ast = parse_statement('x := 1')
    assert isinstance(ast, st.Assign)
    assert ast == st.Assign(st.Name('x'), st.Num('1'))

def test_assignment_statement_with_expression_value():
    ast = parse_statement('x := 1 + 2')
    assert isinstance(ast, st.Assign)
    assert ast == st.Assign(st.Name('x'), st.BinaryOp(tokens.PLUS, st.Num('1'), st.Num('2')))

def test_assignment_statement_with_array_subscript_target():
    ast = parse_statement('x[0] := 1')
    expected = st.Assign(st.Subscript(st.Name('x'), st.Num('0')), st.Num('1'))
    print 'Expected:', expected
    print 'Got:     ', ast
    assert isinstance(ast, st.Assign)
    assert ast == expected
    
def test_assignment_statement_with_array_subscript_expression_target():
    ast = parse_statement('x[1 + 2] := 1')
    expected = st.Assign(st.Subscript(st.Name('x'), st.BinaryOp(tokens.PLUS, st.Num('1'), st.Num('2'))), st.Num('1'))
    print 'Expected:', expected
    print 'Got:     ', ast
    assert isinstance(ast, st.Assign)
    assert ast == expected

# return
def test_return_statement():
    assert parse_statement('return') == tokens.RETURN

# call
def test_call_with_no_args():
    ast = parse_statement('f()')
    assert isinstance(ast, st.Call)
    assert ast == st.Call(st.Name('f'), [])

def test_call_with_one_arg():
    ast = parse_statement('f(x)')
    assert isinstance(ast, st.Call)
    assert ast == st.Call(st.Name('f'), [st.Name('x')])

def test_call_with_two_args():
    ast = parse_statement('f(1, 2)')
    assert isinstance(ast, st.Call)
    assert ast == st.Call(st.Name('f'), [st.Num('1'), st.Num('2')])

@raises(parser.ParseError)
def test_nested_calls():
    ast = parse_statement('f(g(x))')
    print ast
    assert isinstance(ast, st.Call)
    assert isinstance(ast.args[0], st.Call)
    assert ast == st.Call(st.Name('f'), [st.Call(st.Name('g'), [st.Name('x')])])

# if
def test_minimal_if_statement():
    ast = parse_statement('if (1) then return; end if')
    assert isinstance(ast, st.If)
    assert ast == st.If(st.Num('1'), [tokens.RETURN], [])

def test_if_else():
    ast = parse_statement('if (1) then return; else return; end if')
    assert isinstance(ast, st.If)
    assert ast == st.If(st.Num('1'), [tokens.RETURN], [tokens.RETURN])

def test_multiple_if_statements():
    ast = parse_statement('if (1) then return; return; end if')
    assert isinstance(ast, st.If)
    assert ast == st.If(st.Num('1'), [tokens.RETURN, tokens.RETURN], [])

def test_multiple_else_statements():
    ast = parse_statement('if (1) then return; else return; return; end if')
    assert isinstance(ast, st.If)
    assert ast == st.If(st.Num('1'), [tokens.RETURN], [tokens.RETURN, tokens.RETURN])

@raises(parser.ParseError)
def test_missing_parenthesis_in_if_statement():
    parse_statement('if 1 then return; end if')

@raises(parser.ParseError)
def test_missing_then_in_if_statement():
    parse_statement('if (1) return; end if')

@raises(parser.ParseError)
def test_missing_statement_in_if_statement():
    parse_statement('if (1) then end if')

@raises(parser.ParseError)
def test_missing_statement_in_else_statement():
    parse_statement('if (1) then return; else end if')

# loop
def test_minimal_loop_statement():
    ast = parse_statement('for (x := 1; 2) end for')
    assert isinstance(ast, st.For)
    assert ast == st.For(st.Assign(st.Name('x'), st.Num('1')), st.Num('2'), [])

def test_loop_with_one_body_statement():
    ast = parse_statement('for (x := 1; 2) return; end for')
    assert isinstance(ast, st.For)
    assert ast == st.For(st.Assign(st.Name('x'), st.Num('1')), st.Num('2'), [tokens.RETURN])

def test_loop_with_two_body_statements():
    ast = parse_statement('for (x := 1; 2) return; return; end for')
    assert isinstance(ast, st.For)
    assert ast == st.For(st.Assign(st.Name('x'), st.Num('1')), st.Num('2'), [tokens.RETURN, tokens.RETURN])

@raises(parser.ParseError)
def test_loop_missing_assignment():
    parse_statement('for (;2) end for')

@raises(parser.ParseError)
def test_loop_missing_test_expression():
    parse_statement('for (x := 1;) end for')

@raises(parser.ParseError)
def test_loop_missing_semicolon_after_assignment():
    parse_statement('for (x := 1 2) end for')

@raises(parser.ParseError)
def test_loop_missing_parentesis():
    parse_statement('for x := 1; 2 end for')

@raises(parser.ParseError)
def test_loop_missing_end():
    parse_statement('for (x := 1; 2) for')

@raises(parser.ParseError)
def test_loop_missing_semicolon_after_statement():
    parse_statement('for (x := 1; 2) return return end for')

# resync point tests
def test_statements_resync_point_recovers_after_error():
    p = get_parser('if(1) then s = + +; return; end if')
    ast = p.statement()
    expected = st.If(st.Num('1'), [tokens.RETURN], [])
    print 'Expected:', expected
    print 'Got:     ', ast
    assert isinstance(ast, st.If)
    assert p.error_encountered
    assert ast == expected

def test_declarations_resync_point_recovers_after_error():
    p = get_parser('procedure f() 1 1; int i; begin end procedure')
    expected = st.ProcDecl(False, st.Name('f'), [],
                           [st.VarDecl(False, tokens.INT, st.Name('i'), None)], [])
    ast = p.declaration()
    print 'Expected:', expected
    print 'Got:     ', ast
    assert isinstance(ast, st.ProcDecl)
    assert p.error_encountered
    assert ast == expected

# Whole program tests
def parse_program(src):
    return parser.parse_tokens(scanner.tokenize_string(src))

def check_program(src, expected):
    ast = parse_program(src)
    print 'Expected:', expected
    print 'Got:     ', ast

    assert isinstance(ast, st.Program)
    assert isinstance(ast.decls, list)
    assert isinstance(ast.body, list)
    assert ast == expected

def test_minimal_program():
    src = 'program p is begin end program'
    expected = st.Program(st.Name('p'), [], [])
    check_program(src, expected)

def test_program_with_one_declaration():
    src ='program p is int x; begin end program'
    expected = st.Program(st.Name('p'),
                          [st.VarDecl(False, tokens.INT, st.Name('x'), None)], [])
    check_program(src, expected)

def test_program_with_two_declarations():
    src ='program p is int x; int y; begin end program'
    expected = st.Program(st.Name('p'),
        [st.VarDecl(False, tokens.INT, st.Name('x'), None),
         st.VarDecl(False, tokens.INT, st.Name('y'), None)], [])
    check_program(src, expected)

def test_program_with_one_statement():
    src ='program p is begin return; end program'
    expected = st.Program(st.Name('p'), [], [tokens.RETURN])
    check_program(src, expected)

def test_program_with_two_statements():
    src ='program p is begin return; return; end program'
    expected = st.Program(st.Name('p'), [], [tokens.RETURN, tokens.RETURN])
    check_program(src, expected)

def test_program_with_two_declarations_and_two_statement():
    src ='program p is int x; int y; begin return; return; end program'
    expected = st.Program(st.Name('p'),
        [st.VarDecl(False, tokens.INT, st.Name('x'), None),
         st.VarDecl(False, tokens.INT, st.Name('y'), None)],
        [tokens.RETURN, tokens.RETURN])
    check_program(src, expected)

@raises(parser.ParseFailedError)
def test_program_with_resync_error():
    src = 'program p is begin x := +; end program'
    parse_program(src)
    
@raises(parser.ParseFailedError)
def test_program_with_eof_error():
    src = 'program p is begin x := +; end'
    parse_program(src)

def test_parsing_file():
    parser._Parser(scanner.tokenize_file(os.path.join('test', 'test_program.src'))).parse()