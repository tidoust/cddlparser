import unittest
import sys

sys.path.append("..")

from cddlparser.tokens import Tokens, Token
from cddlparser.lexer import Lexer


class TestLexer(unittest.TestCase):
    def test_should_allow_to_read_token(self):
        cddl = "=+(){},/"
        tests = [
            Tokens.ASSIGN,
            Tokens.PLUS,
            Tokens.LPAREN,
            Tokens.RPAREN,
            Tokens.LBRACE,
            Tokens.RBRACE,
            Tokens.COMMA,
            Tokens.TCHOICE,
        ]

        lexer = Lexer(cddl)
        for tokenType in tests:
            token = lexer.nextToken()
            self.assertEqual(token.type, tokenType)

    def test_should_read_identifiers_and_comments(self):
        cddl = "   headers,       \n   ; Headers for the recipient"
        comment = Token(
            Tokens.COMMENT, "; Headers for the recipient", [], "       \n   "
        )
        tests = [
            [Tokens.IDENT, "headers", "   ", None],
            [Tokens.COMMA, "", "", None],
            [Tokens.EOF, "", "", comment],
        ]

        lexer = Lexer(cddl)
        for [tokenType, literal, whitespace, comment] in tests:
            token = lexer.nextToken()
            self.assertEqual(token.type, tokenType)
            self.assertEqual(token.literal, literal)
            self.assertEqual(token.whitespace, whitespace)
            if comment is None:
                self.assertEqual(len(token.comments), 0)
            else:
                self.assertEqual(len(token.comments), 1)
                self.assertEqual(token.comments[0].type, comment.type)
                self.assertEqual(token.comments[0].literal, comment.literal)
                self.assertEqual(token.comments[0].whitespace, comment.whitespace)


if __name__ == "__main__":
    unittest.main()
