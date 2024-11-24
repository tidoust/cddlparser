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
        self._test_parse_file('example.cddl')

    def test_can_parse_compositions(self):
        self._test_parse_file('compositions.cddl')

    def test_can_parse_ranges(self):
        self._test_parse_file('ranges.cddl')

    def test_can_parse_occurrences(self):
        self._test_parse_file('occurrences.cddl')

    def test_can_parse_arrays(self):
        self._test_parse_file('arrays.cddl')

    def test_can_parse_unwrapped_arrays(self):
        self._test_parse_file('unwrapping.cddl')

    def test_can_parse_comments(self):
        self._test_parse_file('comments.cddl')

    def test_can_parse_choices(self):
        self._test_parse_file('choices.cddl')

    def test_can_parse_nested_groups(self):
        self._test_parse_file('nested.cddl')

    def test_can_parse_operators(self):
        self._test_parse_file('operators.cddl')


    def test_serialize_CDDL_file(self):
        self._test_serialize_file('example.cddl')

    def test_serialize_compositions(self):
        self._test_serialize_file('compositions.cddl')

    def test_serialize_ranges(self):
        self._test_serialize_file('ranges.cddl')

    def test_serialize_occurrences(self):
        self._test_serialize_file('occurrences.cddl')

    def test_serialize_arrays(self):
        self._test_serialize_file('arrays.cddl')

    def test_serialize_unwrapped_arrays(self):
        self._test_serialize_file('unwrapping.cddl')

    def test_serialize_comments(self):
        self._test_serialize_file('comments.cddl')

    def test_serialize_choices(self):
        self._test_serialize_file('choices.cddl')

    def test_serialize_nested_groups(self):
        self._test_serialize_file('nested.cddl')

    def test_serialize_operators(self):
        self._test_serialize_file('operators.cddl')


    def _test_parse_file(self, file):
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
            self.assertEqual(pformat(ast.assignments, width=100), snap)
        else:
            # Create the snapshot if it does not exist yet (in other words, to
            # refresh a snapshot, delete it and run tests again)
            fsnap = open(snapfile, 'w')
            fsnap.write(pformat(ast.assignments, width=100))
            fsnap.close()

    def _test_serialize_file(self, file):
        f = open(os.path.join(basepath, '__fixtures__', file), 'r')
        cddl = f.read()
        f.close()
        parser = Parser(cddl)
        ast = parser.parse()
        serialization = ast.str()
        self.assertEqual(serialization, cddl)

