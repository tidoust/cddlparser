import unittest
import sys
sys.path.append('..')

from src.tokens import Tokens
from src.lexer import Lexer

class TestLexer(unittest.TestCase):
    def test_should_allow_to_read_token(self):
        input = '=+(){},/'
        tests = [
            [Tokens.ASSIGN, '='],
            [Tokens.PLUS, '+'],
            [Tokens.LPAREN, '('],
            [Tokens.RPAREN, ')'],
            [Tokens.LBRACE, '{'],
            [Tokens.RBRACE, '}'],
            [Tokens.COMMA, ','],
            [Tokens.SLASH, '/']
        ]

        lexer = Lexer(input)
        for [type, literal] in tests:
            token = lexer.nextToken()
            self.assertEqual(token.type, type)
            self.assertEqual(token.literal, literal)

    def test_should_read_identifiers_and_comments(self):
        input = '   headers,       ; Headers for the recipient'
        tests = [
            [Tokens.IDENT, 'headers'],
            [Tokens.COMMA, ','],
            [Tokens.COMMENT, '; Headers for the recipient']
        ]

        lexer = Lexer(input)
        for [type, literal] in tests:
            token = lexer.nextToken()
            self.assertEqual(token.type, type)
            self.assertEqual(token.literal, literal)

if __name__ == '__main__':
    unittest.main()