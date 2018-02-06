#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys
import unittest
from irods.models import Collection, DataObject
import xml.etree.ElementTree as ET
import logging
import irods.test.helpers as helpers

logger = logging.getLogger(__name__)

UNICODE_TEST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'unicode_sampler.xml')


def to_unicode(data):
    if isinstance(data, bytes):
        return data.decode('utf-8')
    return data


def parse_xml_file(path):
    # parse xml document
    tree = ET.parse(path)

    # default namespace
    nsmap = {'ns': 'http://www.w3.org/1999/xhtml'}

    # get table body
    table = tree.find('.//ns:tbody', nsmap)

    # extract values from table
    unicode_strings = set()
    for row in table:
        values = [to_unicode(column.text) for column in row]

        # split strings in 3rd column
        for token in values[2].split():
            unicode_strings.add(token.strip('()'))

        # split strings in 4th column
        for token in values[3].split():
            unicode_strings.add(token.strip('()'))

    # fyi
    for string in unicode_strings:
        logger.info(string)

    return unicode_strings


class TestUnicodeNames(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()
        self.coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)

        # make list of unicode filenames, from file
        self.names = parse_xml_file(UNICODE_TEST_FILE)

        # Create test collection
        self.coll = helpers.make_collection(
            self.sess, self.coll_path, self.names)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_files(self):
        # Query for all files in test collection
        query = self.sess.query(DataObject.name, Collection.name).filter(
            Collection.name == self.coll_path)

        for result in query:
            # check that we got back one of our original names
            assert result[DataObject.name] in self.names

            # fyi
            logger.info(
                u"{0}/{1}".format(result[Collection.name], result[DataObject.name]))

            # remove from set
            self.names.remove(result[DataObject.name])

        # make sure we got all of them
        self.assertEqual(0, len(self.names))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
