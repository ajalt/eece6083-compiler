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
    assert parse_ex('true') == st.TrueVal
    
def test_literal_false():
    assert parse_ex('false') == st.FalseVal

def test_call():
    ast = parse_ex('func()')
    assert isinstance(ast, st.Call)
    assert ast == st.Call(func=st.Name(id='func'), args=[])
    
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
        'and':tokens.AND,
        'or':tokens.OR,
        '+': tokens.PLUS,
        '-': tokens.MINUS,
        '*': tokens.MULTIPLY,
        '/': tokens.DIVIDE,
        '<': tokens.LT,
        '<=': tokens.LTE,
        '>': tokens.GT,
        '>=': tokens.GTE,
        '!=': tokens.NOTEQUAL,
        '=': tokens.EQUAL,
    }
    
    for op, tok in ops.iteritems():
        yield check_binary_op, op, tok

def check_binary_op(op, tok):
    ast = parse_ex('1 %s 2' % op)
    assert isinstance(ast, st.BinaryOp)
    assert ast == st.BinaryOp(tok, st.Num('1'), st.Num('2'))
    
def test_parenthesis_equal_containing_expression():
    exp = '1 + 2'
    assert parse_ex('(%s)' % exp) == parse_ex(exp)
    
def test_parenthesis_grouping():
    assert parse_ex('2 * (1 + 3)') == st.BinaryOp(tokens.MULTIPLY, st.Num('2'),
                                st.BinaryOp(tokens.PLUS, st.Num('1'), st.Num('3')))
    
def test_subscript():
    ast = parse_ex('a[1]')
    print ast
    assert isinstance(ast, st.Subscript)
    assert ast == (st.Name('a'), st.Num('1'))
    
def test_call_with_no_args():
    ast = parse_ex('f()')
    assert isinstance(ast, st.Call)
    assert ast == st.Call(st.Name('f'), [])
    
def test_call_with_one_arg():
    ast = parse_ex('f(x)')
    assert isinstance(ast, st.Call)
    assert ast == st.Call(st.Name('f'), [st.Name('x')])
    
def test_call_with_two_args():
    ast = parse_ex('f(1, 2)')
    assert isinstance(ast, st.Call)
    assert ast == st.Call(st.Name('f'), [st.Num('1'), st.Num('2')])
    
def test_nested_calls():
    ast = parse_ex('f(g(x))')
    print ast
    assert isinstance(ast, st.Call)
    assert isinstance(ast.args[0], st.Call)
    assert ast == st.Call(st.Name('f'), [st.Call(st.Name('g'), [st.Name('x')])])
    
    
# declaration tests

def parse_decl(src):
    return get_parser(src).declaration()

def test_type_decls():
    types = {
        'string': tokens.STRING_KEYWORD,
        'int': tokens.INT,
        'bool': tokens.BOOL,
        'float': tokens.FLOAT,
    }
    for name, tok in types.iteritems():
        for is_global in (True, False):
            for array_len in (None, '0', '1'):
                yield check_type_decl, is_global, name, tok, array_len
    
def check_type_decl(is_global, name, tok, array_len):
    ast = parse_decl('%s %s x%s' %
                     ('global' if is_global else '',name,
                      '[%s]' % array_len if array_len is not None else ''))
    expected = st.VarDecl(is_global, tok, st.Name('x'), array_len)
    print 'Got:     ',ast
    print 'Expected:', expected
    assert isinstance(ast, st.VarDecl)
    assert ast == expected
    
    

    
