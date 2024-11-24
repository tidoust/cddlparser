import unittest
import os
import sys
import re
from pprint import pformat

sys.path.append('..')
from src.parser import Parser

basepath = os.path.dirname(os.path.realpath(__file__))

class TestParser(unittest.TestCase):
    maxDiff = None

    def test_should_correctly_parse_CDDL_file(self):
        self._testFile('example.cddl')

    def test_can_parse_compositions(self):
        self._testFile('compositions.cddl')

    def test_can_parse_ranges(self):
        self._testFile('ranges.cddl')

    def test_can_parse_occurrences(self):
        self._testFile('occurrences.cddl')

    def test_can_parse_arrays(self):
        self._testFile('arrays.cddl')

    def test_can_parse_unwrapped_arrays(self):
        self._testFile('unwrapping.cddl')

    def test_can_parse_comments(self):
        self._testFile('comments.cddl')

    def test_can_parse_choices(self):
        self._testFile('choices.cddl')

    def test_can_parse_nested_groups(self):
        self._testFile('nested.cddl')

    def test_can_parse_operators(self):
        self._testFile('operators.cddl')

    def _testFile(self, file):
        f = open(os.path.join(basepath, '__fixtures__', file), 'r')
        cddl = f.read()
        f.close()
        parser = Parser(cddl)
        ast = parser.parse()

        snapfile = os.path.join(basepath, '__snapshots__', re.sub(r'\.cddl$', '.snap', file))
        if os.path.exists(snapfile):
            # Compare with snapshot if it exists
            fsnap = open(snapfile, 'r')
            snap = fsnap.read()
            fsnap.close()
            self.assertEqual(pformat(ast, width=100), snap)
        else:
            # Create the snapshot if it does not exist yet (in other words, to
            # refresh a snapshot, delete it and run tests again)
            fsnap = open(snapfile, 'w')
            fsnap.write(pformat(ast, width=100))
            fsnap.close()
