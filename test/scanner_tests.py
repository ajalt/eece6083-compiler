from nose.tools import raises
import string
import os
import itertools

from src import scanner
from src import tokens

def _get_single_token(line):
    return next(scanner.tokenize_line(line))

def test_individual_tokens():
    for line, token_type in scanner.token_map.iteritems():
        yield check_token, line, token_type
        
def check_token(line, token_type):
    token = _get_single_token(line)
    print tuple(token), (token_type, line, 0, len(line) - 1, 0, line) 
    assert token == (token_type, line, 0, len(line) - 1, 0, line)
        
def test_numbers():
    for line in ('1',
                '11',
                '1.',
                '1.1',
                '1_',
                '1_.',
                '1_._',
                '1.1',
                '1.1_',
                '1_._1_'
                 ):
        yield check_number, line

def check_number(line):
    token = _get_single_token(line)
    expected = (tokens.NUMBER, line.replace('_', ''), 0, len(line) - 1, 0, line) 
    print tuple(token), expected
    assert token == expected
    
def test_single_character_ambiguous_terminals():
    # Although these token types are tested in the previous function, the
    # scanner follows a different code path when an ambiguous terminal is at the
    # end of a line then when the character has another character after it.
    for line, token_type in (('< ', tokens.LT),
                             ('> ', tokens.GT),
                             (': ', tokens.COLON)
                            ):
        yield check_single_character_ambiguous_terminal, line, token_type
        
def check_single_character_ambiguous_terminal(line, token_type):
    token = _get_single_token(line)
    print tuple(token), (token_type, line[0], 0, 0, 0, line) 
    assert token == (token_type, line[0], 0, 0, 0, line)

def test_legal_strings():
    for line in ('""',
                 '"s"',
                 ''.join(('"', string.letters, string.digits, ' _,;:."')),
                 ):
        yield check_string_token, line

def check_string_token(line):
    assert _get_single_token(line) == (tokens.STRING, line, 0, len(line) - 1, 0, line)
  
def test_for_error_tokens():
    for line in ('"@"', # illegal character in string
                 '"', # EOL in string
                 '!', # '!' at EOL
                 '@', # illegal character
                 '.', # dot by itself shouldn't be a number
                 ):
        yield check_for_error, line
        
def test_for_illegal_character_after_exclamation_point():
    return check_for_error('!*', 1)

def test_for_underscore_at_beginnig_of_number():
    return check_for_error('_2', end=0)
    
def check_for_error(line, start=0, end=None):
    if end is None:
        end = len(line) - 1
    token = _get_single_token(line)
    assert token[0] == tokens.ERROR
    print token[2:], (start, end, 0, line)
    assert token[2:] == (start, end, 0, line)
    
def test_lines_with_no_tokens():
    for line in (' ',
                 '\t',
                 '\r',
                 '\n',
                 '//comment'
                 ):
        yield check_for_stop_iteration, line
    
@raises(StopIteration)
def check_for_stop_iteration(line):
    _get_single_token(line)
    
def test_full_line():
    # end the line with an unmatched quote to get an error token
    lexemes = list(s + ' ' for s in scanner.token_map) + ['2', '"string"', '"']
    result = list(scanner.tokenize_line(''.join(lexemes)))
    print 'Result len:', len(result), 'Expected:', len(lexemes)
    for res, exp in itertools.izip_longest(result, lexemes):
        print res[:2], exp
    assert len(result) == len(lexemes)
    
def test_file():
    token_list = list(scanner.tokenize_file(os.path.join('test', 'test_source.txt')))
    print len(token_list)
    assert len(token_list) == 57
