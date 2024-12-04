from .src.parser import Parser
from .src.ast import Marker
from .src.tokens import Token, Tokens
from .src import ast

__all__ = ["Marker", "Token", "Tokens", "ast"]


def parse(string) -> ast.CDDLTree:
    parser = Parser(string)
    return parser.parse()
