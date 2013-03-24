import itertools

from nose.tools import raises

from src import scanner
from src import tokens
from src import parser
from src import syntaxtree as st
from src import typechecker
from src import optimizer

from src.syntaxtree import *

def get_parser(src):
    return parser.Parser(scanner.tokenize_string(src))

def parse_ex(exp):
    ast = get_parser(exp).expression()
    typechecker.Checker().get_type(ast)
    return ast

def parse_prog(src):
    ast = parser.parse_tokens(scanner.tokenize_string(src))
    assert typechecker.tree_is_valid(ast)
    return ast

def fold_ex(exp):
    return optimizer.ConstantFolder().walk(parse_ex(exp))

# -- ConstantFolder tests --
def check_folding_expression(src, expected):
    got = fold_ex(src)
    print 'Source:  ', src
    print 'Expected:', expected
    print 'Got:     ', got
    assert expected == got
    
def test_folding_binops():
    for operator, result in (
        ('+', '5'),
        ('-', '-1'),
        ('*', '6'),
        ('/', '0'),
        ('&', '2'),
        ('|', '3'),
        ('<',  tokens.TRUE),
        ('>', tokens.FALSE),
        ('<=', tokens.TRUE),
        ('>=', tokens.FALSE),
        ('==', tokens.FALSE),
    ):
        src = '2 %s 3' % operator
        expected = st.Num(result)
        yield check_folding_expression, src, expected
        
def test_folding_boolean_binops():
    bools = (tokens.FALSE, tokens.TRUE)
    testops = (tokens.AND, tokens.OR)
    pythonops = ('and', 'or')
    
    for a, b, op in itertools.product((0,1),(0,1),(0,1)):
        src = '%s %s %s' % (bools[a], testops[op], bools[b])
        expected = bools[eval('%s %s %s' % (a, pythonops[op], b))]
        yield check_folding_expression, src, st.Num(expected)
        
def test_folding_unary_minus():
    check_folding_expression('-3', st.Num('-3'))
    
def test_folding_unary_not():
    yield check_folding_expression, 'not 4294967280', st.Num('15')
    yield check_folding_expression, 'not true', st.Num(tokens.FALSE)
    yield check_folding_expression, 'not false', st.Num(tokens.TRUE)
    
    
# -- ConstantPropagator tests--

def check_propagation(src, expected_body):
    got = optimizer.ConstantPropagator().walk(parse_prog(src))
    print 'Expected:', expected_body
    print 'Got body:', got.body
    assert expected_body == got.body
    
def test_single_propagation():
    src = '''
    program test_program is
    int a;
    int b;
    begin
        a := 1;
        b := a;
    end program
    '''
    expected_body = [st.Assign(st.Name('a'), st.Num('1')), st.Assign(st.Name('b'), st.Num('1'))]
    check_propagation(src, expected_body)
    
def test_single_propagation_in_fold():
    src = '''
    program test_program is
    int a;
    int b;
    begin
        a := 1;
        b := 1 + a;
    end program
    '''
    expected_body = [st.Assign(st.Name('a'), st.Num('1')), st.Assign(st.Name('b'), st.Num('2'))]
    check_propagation(src, expected_body)
    
def test_propagation_in_branch():
    src = '''
    program test_program is
    int a;
    int b;
    begin
        if (1) then
            a := 1;
        end if;
        b := a;
    end program
    '''
    expected_body = [
        If(
          test=Num('1'),
          body=[
            Assign(
              target=Name('a'),
              value=Num('1'))],
          orelse=[]),
        Assign(
          target=Name('b'),
          value=Name('a'))
    ]
    check_propagation(src, expected_body)
    
def test_propagation_to_call():
    src = '''
    program test_program is
        int a;
        procedure f(int x in)
        begin
        end procedure;
    begin
        a := 1;
        f(a);
    end program
    '''
    expected_body = [
        Assign(
          target=Name('a'),
          value=Num('1')),
        Call(
          func=Name('f'),
          args=[
            Num(
              n=Num('1'))])
    ]

    check_propagation(src, expected_body)
    
def test_invalidation_in_branch():
    src = '''
    program test_program is
    int a;
    int b;
    begin
        a := 1;
        if (1) then
            a := 2;
        end if;
        b := a;
    end program
    '''
    expected_body = [
        Assign(
          target=Name('a'),
          value=Num('1')),
        If(
          test=Num('1'),
          body=[
            Assign(
              target=Name('a'),
              value=Num('2'))],
          orelse=[]),
        Assign(
          target=Name('b'),
          value=Name('a'))
    ]
    check_propagation(src, expected_body)
    
def test_propagation_in_loop():
    src = '''
    program test_program is
    int a;
    int b;
    begin
        for (a := 1; 1) 
        end for;
        b := a;
    end program
    '''
    expected_body = [
        For(
          assignment=Assign(
            target=Name('a'),
            value=Num('1')),
          test=Num('1'),
          body=[]),
        Assign(
          target=Name('b'),
          value=Name('a'))
    ]
    check_propagation(src, expected_body)
    
def test_invalidation_in_loop():
    src = '''
    program test_program is
    int a;
    int b;
    begin
        a := 1;
        for (a := 2; 1) 
        end for;
        b := a;
    end program
    '''
    expected_body = [
        Assign(
          target=Name('a'),
          value=Num('1')),
        For(
          assignment=Assign(
            target=Name('a'),
            value=Num('2')),
          test=Num('1'),
          body=[]),
        Assign(
          target=Name('b'),
          value=Name('a'))]
    check_propagation(src, expected_body)
    
# -- DeadCodeEliminator tests --

def check_elimination(src, expected_program):
    got = optimizer.DeadCodeEliminator().walk(parse_prog(src))
    print 'Expected:', expected_program
    print 'Got:     ', got
    assert expected_program == got
    
def check_complete_elimination(src):
    expected_program = Program(
        name=Name('test_program'),
        decls=[],
        body=[])
    
    check_elimination(src, expected_program)

def test_unused_variable_declaration():
    src = '''
    program test_program is
    int a;
    begin
    end program
    '''
    check_complete_elimination(src)
    

def test_unused_procedure_declaration():
    src = '''
    program test_program is
    procedure f(int x in)
        begin
        end procedure;
    begin
    end program
    '''
    check_complete_elimination(src)
    
def test_unused_assignment():
    src = '''
    program test_program is
        int a;
    begin
        a := 1;
    end program
    '''
    check_complete_elimination(src)
        
def test_unused_loop():
    src = '''
    program test_program is
        int a;
    begin
        for(a := 0; 0)
            a := 1;
        end for;
    end program
    '''
    check_complete_elimination(src)
    
def test_early_return():
    src = '''
    program test_program is
        procedure f(int x in)
        begin
        end procedure;
    begin
        f(1);
        return;
        f(2);
    end program
    '''
    expected_program = Program(
        name=Name('test_program'),
        decls=[
          ProcDecl(
            is_global=False,
            name=Name('f'),
            params=[
              Param(
                var_decl=VarDecl(
                  is_global=False,
                  type='int',
                  name=Name('x'),
                  array_length=None),
                direction='in')],
            decls=[],
            body=[])],
        body=[
          Call(
            func=Name('f'),
            args=[
              Num('1')])])
    check_elimination(src, expected_program)
    
def test_branch_always_taken():
    src = '''
    program test_program is
        procedure f(int x in)
        begin
        end procedure;
    begin
        if(1) then
            f(1);
        end if;
    end program
    '''
    expected_program = Program(
        name=Name('test_program'),
        decls=[
          ProcDecl(
            is_global=False,
            name=Name('f'),
            params=[
              Param(
                var_decl=VarDecl(
                  is_global=False,
                  type='int',
                  name=Name('x'),
                  array_length=None),
                direction='in')],
            decls=[],
            body=[])],
        body=[
          Call(
            func=Name('f'),
            args=[
              Num('1')])])
    check_elimination(src, expected_program)

def test_branch_never_taken():
    src = '''
    program test_program is
        procedure f(int x in)
        begin
        end procedure;
    begin
        if(0) then
            f(1);
        else
            f(2);
        end if;
    end program
    '''
    expected_program = Program(
        name=Name('test_program'),
        decls=[
          ProcDecl(
            is_global=False,
            name=Name('f'),
            params=[
              Param(
                var_decl=VarDecl(
                  is_global=False,
                  type='int',
                  name=Name('x'),
                  array_length=None),
                direction='in')],
            decls=[],
            body=[])],
        body=[
          Call(
            func=Name('f'),
            args=[
              Num('2')])])
    check_elimination(src, expected_program)
    
def test_in_param_invalidaiton():
    src = '''
    program test_program is
        int a;
        procedure f(int x in)
        begin
        end procedure;
    begin
        f(a);
    end program
    '''
    expected_program = Program(
        name=Name('test_program'),
        decls=[
          VarDecl(
            is_global=False,
            type='int',
            name=Name('a'),
            array_length=None),
          ProcDecl(
            is_global=False,
            name=Name('f'),
            params=[
              Param(
                var_decl=VarDecl(
                  is_global=False,
                  type='int',
                  name=Name('x'),
                  array_length=None),
                direction='in')],
            decls=[],
            body=[])],
        body=[
          Call(
            func=Name('f'),
            args=[
              Name('a')])])

    check_elimination(src, expected_program)
    
def test_out_param_invalidaiton():
    src = '''
    program test_program is
        int a;
        procedure f(int x out)
        begin
        end procedure;
    begin
        a := 1;
        f(a);
    end program
    '''
    expected_program = Program(
        name=Name('test_program'),
        decls=[
          VarDecl(
            is_global=False,
            type='int',
            name=Name('a'),
            array_length=None),
          ProcDecl(
            is_global=False,
            name=Name('f'),
            params=[
              Param(
                var_decl=VarDecl(
                  is_global=False,
                  type='int',
                  name=Name('x'),
                  array_length=None),
                direction='out')],
            decls=[],
            body=[])],
        body=[
          Call(
            func=Name('f'),
            args=[
              Name('a')])])

    check_elimination(src, expected_program)
    

# -- Functional tests --

def check_On(level, expected_program):
    src = '''
    program test_program is
    int a;
    int b;
    int c;
    int r;
    begin
        a := 15 + 15;
        b := 9 - a / (2 + 3);
        c :=  b * 4;
        if (c > 10) then
            c := c - 10;
        end if;
        r := c * (60 / a);
    end program
    '''
    assert optimizer.optimize_tree(parse_prog(src), level) == expected_program

def test_O0():
    expected_program = Program(
        name=Name('test_program'),
        decls=[
          VarDecl(
            is_global=False,
            type='int',
            name=Name('a'),
            array_length=None),
          VarDecl(
            is_global=False,
            type='int',
            name=Name('b'),
            array_length=None),
          VarDecl(
            is_global=False,
            type='int',
            name=Name('c'),
            array_length=None),
          VarDecl(
            is_global=False,
            type='int',
            name=Name('r'),
            array_length=None)],
        body=[
          Assign(
            target=Name('a'),
            value=BinaryOp(
              op='+',
              left=Num('15'),
              right=Num('15'))),
          Assign(
            target=Name('b'),
            value=BinaryOp(
              op='-',
              left=Num('9'),
              right=BinaryOp(
                op='/',
                left=Name('a'),
                right=BinaryOp(
                  op='+',
                  left=Num('2'),
                  right=Num('3'))))),
          Assign(
            target=Name('c'),
            value=BinaryOp(
              op='*',
              left=Name('b'),
              right=Num('4'))),
          If(
            test=BinaryOp(
              op='>',
              left=Name('c'),
              right=Num('10')),
            body=[
              Assign(
                target=Name('c'),
                value=BinaryOp(
                  op='-',
                  left=Name('c'),
                  right=Num('10')))],
            orelse=[]),
          Assign(
            target=Name('r'),
            value=BinaryOp(
              op='*',
              left=Name('c'),
              right=BinaryOp(
                op='/',
                left=Num('60'),
                right=Name('a'))))])
    
def test_O1():
    expected_program = Program(
        name=Name('test_program'),
        decls=[
          VarDecl(
            is_global=False,
            type='int',
            name=Name('a'),
            array_length=None),
          VarDecl(
            is_global=False,
            type='int',
            name=Name('b'),
            array_length=None),
          VarDecl(
            is_global=False,
            type='int',
            name=Name('c'),
            array_length=None),
          VarDecl(
            is_global=False,
            type='int',
            name=Name('r'),
            array_length=None)],
        body=[
          Assign(
            target=Name('a'),
            value=Num('30')),
          Assign(
            target=Name('b'),
            value=BinaryOp(
              op='-',
              left=Num('9'),
              right=BinaryOp(
                op='/',
                left=Name('a'),
                right=Num('5')))),
          Assign(
            target=Name('c'),
            value=BinaryOp(
              op='*',
              left=Name('b'),
              right=Num('4'))),
          If(
            test=BinaryOp(
              op='>',
              left=Name('c'),
              right=Num('10')),
            body=[
              Assign(
                target=Name('c'),
                value=BinaryOp(
                  op='-',
                  left=Name('c'),
                  right=Num('10')))],
            orelse=[]),
          Assign(
            target=Name('r'),
            value=BinaryOp(
              op='*',
              left=Name('c'),
              right=BinaryOp(
                op='/',
                left=Num('60'),
                right=Name('a'))))])
    check_On(1, expected_program)
    
def test_O2():
    expected_program = Program(
        name=Name('test_program'),
        decls=[],
        body=[])
    check_On(2, expected_program)

    

    

