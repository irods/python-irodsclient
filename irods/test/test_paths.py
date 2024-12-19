import unittest
import os.path
from irods.path import iRODSPath

_normalization_test_cases = [
    #  -- test case --                  -- reference --
    ("/zone", "/zone"),  # a normal path (1 element)
    ("/zone/", "/zone"),  # single-slash (1 element)
    ("/zone/abc", "/zone/abc"),  # a normal path (2 elements)
    ("/zone/abc/", "/zone/abc"),  # single-slash (2 elements)
    ("/zone/abc/.", "/zone/abc"),  # final "."
    ("/zone/abc/./", "/zone/abc"),  # final "." and "/"
    ("/zone/abc/..", "/zone"),  # final ".."
    ("/zone/abc/../", "/zone"),  # final ".." and "/"
    ("/zone1/../zone2", "/zone2"),  # replace one path element with another
    ("/zone/home1/../home2", "/zone/home2"),  # same for a later path element
    ("/..", "/"),  # go up (1x) above root collection
    ("/../..", "/"),  # go up (2x) above root collection
    ("", "/"),  # absolute makes a blank into the root collection
    (".", "/"),  # absolute makes a single "." into the root collection
    ("./.", "/"),  # absolute makes "." (2x) into the root collection
    (
        "././zone",
        "/zone",
    ),  # absolute makes initial "." (2x) a NO-OP before a normal elem
    ("/./zone/abc", "/zone/abc"),  # initial (no-op) '.'
    ("/../zone", "/zone"),  # go up (1x) above root collection and back down
    ("/../zone/..", "/"),  # go up (when first, this is a NO-OP); then down, up
    ("/../../zone", "/zone"),  # go up (2x) above root collection and back down
    ("//zone1/../.././zone2", "/zone2"),  # double-slashes, multiple relative elems
    (
        "//zone1//../.././zone2",
        "/zone2",
    ),  # double-slashes (2x), multiple relative elems
    ("//zone//abc/.", "/zone/abc"),  # same with final "."
    ("//zone//abc/..", "/zone"),  # same with final ".."
    ("//zone//abc/./..", "/zone"),  # same with final "." and ".."
    ("/zone//abc/./../", "/zone"),  # mixed relative elems (./..) and final slashes
    ("/zone//abc/.././", "/zone"),  # mixed relative elems (../.) and final slashes
    (
        "/zone/home1//user/./../trash",
        "/zone/home1/trash",
    ),  # intermediately situated double-slash and relative elems (vsn 1)
    (
        "/zone/home1//user/.././trash",
        "/zone/home1/trash",
    ),  # intermediately situated double-slash and relative elems (vsn 2)
]


class PathsTest(unittest.TestCase):
    def test_path_normalization__383(self):
        for test_path, reference in _normalization_test_cases:
            normalized_path = iRODSPath(test_path)
            self.assertEqual(normalized_path, reference)


if __name__ == "__main__":
    import sys

    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
