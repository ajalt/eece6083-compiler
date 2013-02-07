from nose.tools import raises

import string
import os
import itertools

from src import scanner
from src import tokens
from src import parser
from src import syntaxtree

# expression tests
def parse_ex(exp):
    return parser._Parser(scanner.tokenize_string(exp)).expression()

def test_number():
    n = '123'
    assert parse_ex(n) == syntaxtree.Num(n) 

def test_name():
    n = 'name'
    assert parse_ex(n) == syntaxtree.Name(n)

def test_str():
    s = '"str"'
    assert parse_ex(s) == syntaxtree.Str(s)

def test_call():
    f = 'func'
    assert parse_ex('%s()' % f) == syntaxtree.Call(func=syntaxtree.Name(id=f), args=[])
