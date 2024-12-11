from .parser import Parser
from .ast import Marker
from .errors import ParserError
from .tokens import Token, Tokens
from . import ast

__all__ = ["Marker", "Token", "Tokens", "ParserError", "ast"]


def parse(string: str) -> ast.CDDLTree:
    parser = Parser(string)
    return parser.parse()
