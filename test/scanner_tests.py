from nose.tools import raises
import string

from src import scanner
from src import tokens

def _get_single_token(string):
    return next(scanner.tokenize_line(string))

def test_individual_tokens():
    for string, token_type in scanner.token_map.iteritems():
        yield check_token, string, token_type

def check_token(string, token_type):
    assert _get_single_token(string) == (token_type, string, 0, len(string) - 1, 0, string)

def test_legal_strings():
    for line in ('""',
                 '"s"',
                 ''.join(('"', string.letters, string.digits, ' _,;:."')),
                 ):
        yield check_string, line

def check_string(line):
    assert _get_single_token(line) == (tokens.STRING, line, 0, len(line) - 1, 0, line)
    
    
@raises(StopIteration)
def test_illegal_character_in_string():
    _get_single_token('"@"')
    
@raises(StopIteration)
def test_eol_in_string():
    _get_single_token('"')
    

