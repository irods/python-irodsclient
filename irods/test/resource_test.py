#! /usr/bin/env python
from __future__ import absolute_import
import os
import six
import sys
import unittest

from irods.test import helpers

class TestResource(unittest.TestCase):

    from helpers import create_simple_resc_hierarchy

    def setUp(self):
        self.sess = helpers.make_session()

    def test_resource_properties_for_parent_and_hierarchy_at_3_levels__392(self):
        ses = self.sess
        root = "deferred_392"
        pt = "pt_392"
        leaf = "leaf_392"
        root_resc = ses.resources.create(root,"deferred")
        try:
            # Create two (passthru + storage) hierarchies below the root: ie. pt0;leaf0 and pt1;leaf1
            with self.create_simple_resc_hierarchy(pt + "_0", leaf + "_0"), \
                 self.create_simple_resc_hierarchy(pt + "_1", leaf + "_1"):
                try:
                    # Adopt both passthru's as children under the main root (deferred) node.
                    ses.resources.add_child(root, pt + "_0")
                    ses.resources.add_child(root, pt + "_1")
                    # Now we have two different 3-deep hierarchies (root;pt0;leaf0 and root;pt1;leaf) sharing the same root node.
                    # Descend each and make sure the relationships hold
                    for mid in root_resc.children:
                        hierarchy = [root_resc, mid, mid.children[0]]
                        parent_resc = None
                        hier_str = root
                        # Assert that the hierarchy and parent properties hold at each level, in both tree branches.
                        for n,resc in enumerate(hierarchy):
                            if n > 0:
                                hier_str += ";{}".format(resc.name)
                            self.assertEqual(resc.parent_id, (None if n == 0 else parent_resc.id))
                            self.assertEqual(resc.parent_name, (None if n == 0 else parent_resc.name))
                            self.assertEqual(resc.hierarchy_string, hier_str)
                            self.assertIs(type(resc.hierarchy_string), str)                   # type of hierarchy field is string.
                            if resc.parent is None:
                                self.assertIs(resc.parent_id, None)
                                self.assertIs(resc.parent_name, None)
                            else:
                                self.assertIn(type(resc.parent_id), six.integer_types) # type of a non-null id field is integer.
                                self.assertIs(type(resc.parent_name), str)             # type of a non-null name field is string.
                            parent_resc = resc
                finally:
                    ses.resources.remove_child(root, pt + "_0")
                    ses.resources.remove_child(root, pt + "_1")
        finally:
            ses.resources.remove(root)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
