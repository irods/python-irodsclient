#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys
import unittest
from irods.models import Collection, DataObject
import xml.etree.ElementTree as ET
from irods.message import (ET as ET_set, XML_Parser_Type, current_XML_parser, default_XML_parser)
import logging
import irods.test.helpers as helpers
from six import PY3

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

    def test_object_name_containing_unicode__318(self):
        dataname = u"réprouvé"
        homepath = helpers.home_collection( self.sess )
        try:
            ET_set( XML_Parser_Type.QUASI_XML, self.sess.server_version )
            path = homepath + "/" + dataname
            self.sess.data_objects.create( path )
        finally:
            ET_set( None )
            self.sess.data_objects.unlink (path, force = True)

        # assert successful switch back to global default
        self.assertIs( current_XML_parser(), default_XML_parser() )

    def test_files(self):
        # Query for all files in test collection
        query = self.sess.query(DataObject.name, Collection.name).filter(
            Collection.name == self.coll_path)

        # Python2 compatibility note:  In keeping with the principle of least surprise, we now ensure
        # queries return values of 'str' type in Python2.  When and if these quantities have a possibility
        # of representing unicode quantities, they can then go through a decode stage.

        encode_unless_PY3 = (lambda x:x) if PY3 else (lambda x:x.encode('utf8'))
        decode_unless_PY3 = (lambda x:x) if PY3 else (lambda x:x.decode('utf8'))

        for result in query:
            # check that we got back one of our original names
            assert result[DataObject.name] in ( [encode_unless_PY3(n) for n in self.names] )

            # fyi
            logger.info( u"{0}/{1}".format( decode_unless_PY3(result[Collection.name]),
                                            decode_unless_PY3(result[DataObject.name]) )
                       )

            # remove from set
            self.names.remove(decode_unless_PY3(result[DataObject.name]))

        # make sure we got all of them
        self.assertEqual(0, len(self.names))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
