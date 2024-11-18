import sys
from pprint import pprint
from src.parser import Parser

def parse(str):
    parser = Parser(str)
    return parser.parse()

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print('Please provide a CDDL file as parameter')
        print('Ex: python cddlparser.py tests/__fixtures__/example.cddl')
    else:
        file = sys.argv[1]
        f = open(file, 'r')
        cddl = f.read()
        f.close()
        ast = parse(cddl)
        pprint(ast)
