import unittest
import os
import sys
import re

sys.path.append("..")
from cddlparser.parser import Parser

basepath = os.path.dirname(os.path.realpath(__file__))


class TestParser(unittest.TestCase):
    maxDiff = None
    files: list = []

    @classmethod
    def setUpClass(cls):
        fixturesPath = os.path.join(basepath, "__fixtures__")
        cls.files = [
            f
            for f in os.listdir(fixturesPath)
            if os.path.isfile(os.path.join(fixturesPath, f))
        ]

        rfcPath = os.path.join(fixturesPath, "rfc")
        cls.rfcs = [
            f for f in os.listdir(rfcPath) if os.path.isfile(os.path.join(rfcPath, f))
        ]

    def test_parse_CDDL(self):
        for file in self.files:
            with self.subTest(file):
                self._test_parse_file(file)

    def test_serialize_CDDL(self):
        for file in self.files:
            with self.subTest(file):
                self._test_serialize_file("", file)

    def test_serialize_RFC(self):
        for file in self.rfcs:
            with self.subTest(file):
                self._test_serialize_file("rfc", file)

    def _test_parse_file(self, file):
        with open(
            os.path.join(basepath, "__fixtures__", file), "r", encoding="utf8"
        ) as fhandle:
            cddl = fhandle.read()
        parser = Parser(cddl)
        ast = parser.parse()

        snapfile = os.path.join(
            basepath, "__snapshots__", re.sub(r"\.cddl$", ".snap", file)
        )
        if os.path.exists(snapfile):
            # Compare with snapshot if it exists
            with open(snapfile, "r", encoding="utf8") as fsnap:
                snap = fsnap.read()
            self.assertEqual(repr(ast), snap)
        else:
            # Create the snapshot if it does not exist yet (in other words, to
            # refresh a snapshot, delete it and run tests again)
            with open(snapfile, "w", encoding="utf8") as fsnap:
                fsnap.write(repr(ast))

    def _test_serialize_file(self, path, file):
        with open(
            os.path.join(basepath, "__fixtures__", path, file), "r", encoding="utf8"
        ) as fhandle:
            cddl = fhandle.read()
        parser = Parser(cddl)
        ast = parser.parse()
        serialization = ast.serialize()
        self.assertEqual(serialization, cddl)
