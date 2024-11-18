from pprint import pprint
from src.parser import Parser

def parse(str):
    parser = Parser(str)
    return parser.parse()

if __name__ == '__main__':
  ast = parse('''
    person = {
      identity,                         ; an identity
      employer: tstr,                   ; some employer
    }
    ''')
  pprint(ast)