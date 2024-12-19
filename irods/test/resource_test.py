#! /usr/bin/env python

import os
import sys
import unittest

import irods.exception as ex
import irods.keywords as kw
import irods.test.helpers as helpers


class TestResource(unittest.TestCase):

    create_simple_resc_hierarchy = helpers.create_simple_resc_hierarchy
    create_simple_resc = helpers.create_simple_resc

    def setUp(self):
        self.sess = helpers.make_session()

    def test_resource_properties_for_parent_and_hierarchy_at_3_levels__392(self):
        ses = self.sess
        root = "deferred_392"
        pt = "pt_392"
        leaf = "leaf_392"
        root_resc = ses.resources.create(root, "deferred")
        try:
            # Create two (passthru + storage) hierarchies below the root: ie. pt0;leaf0 and pt1;leaf1
            with self.create_simple_resc_hierarchy(
                pt + "_0", leaf + "_0"
            ), self.create_simple_resc_hierarchy(pt + "_1", leaf + "_1"):
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
                        for n, resc in enumerate(hierarchy):
                            if n > 0:
                                hier_str += ";{}".format(resc.name)
                            self.assertEqual(
                                resc.parent_id, (None if n == 0 else parent_resc.id)
                            )
                            self.assertEqual(
                                resc.parent_name, (None if n == 0 else parent_resc.name)
                            )
                            self.assertEqual(resc.hierarchy_string, hier_str)
                            self.assertIs(
                                type(resc.hierarchy_string), str
                            )  # type of hierarchy field is string.
                            if resc.parent is None:
                                self.assertIs(resc.parent_id, None)
                                self.assertIs(resc.parent_name, None)
                            else:
                                self.assertIs(
                                    type(resc.parent_id), int
                                )  # type of a non-null id field is integer.
                                self.assertIs(
                                    type(resc.parent_name), str
                                )  # type of a non-null name field is string.
                            parent_resc = resc
                finally:
                    ses.resources.remove_child(root, pt + "_0")
                    ses.resources.remove_child(root, pt + "_1")
        finally:
            ses.resources.remove(root)

    def test_put_with_violating_minimum_free_space__issue_462(self):
        small_file = large_file = ""
        data = []
        with self.create_simple_resc() as newResc:
            try:
                resc = self.sess.resources.get(newResc)
                resc.modify("free_space", "10000")
                resc.modify("context", "minimum_free_space_for_create_in_bytes=20000")

                small_file = "small_file_462"
                with open(small_file, "wb") as small:
                    small.write(b"." * 1024)
                home = helpers.home_collection(self.sess)
                put_opts = {kw.DEST_RESC_NAME_KW: newResc}
                with self.assertRaises(ex.USER_FILE_TOO_LARGE):
                    data.append(
                        self.sess.data_objects.put(
                            small_file,
                            "{home}/{small_file}".format(**locals()),
                            return_data_object=True,
                            **put_opts
                        )
                    )

                large_file = "large_file_462"
                with open(large_file, "wb") as large:
                    large.write(b"." * 1024**2 * 40)
                with self.assertRaises(ex.USER_FILE_TOO_LARGE):
                    data.append(
                        self.sess.data_objects.put(
                            large_file,
                            "{home}/{large_file}".format(**locals()),
                            return_data_object=True,
                            **put_opts
                        )
                    )
            finally:
                for d in data:
                    d.unlink(force=True)
                for _ in [small_file, large_file]:
                    if _:
                        os.unlink(_)


if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath("../.."))
    unittest.main()
