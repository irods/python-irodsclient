#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys
import time
import datetime
import unittest
from irods.meta import (iRODSMeta, AVUOperation, BadAVUOperationValue, BadAVUOperationKeyword)
from irods.manager.metadata_manager import InvalidAtomicAVURequest
from irods.models import (DataObject, Collection, Resource, CollectionMeta)
import irods.test.helpers as helpers
import irods.keywords as kw
from irods.session import iRODSSession
from six.moves import range
from six import PY2, PY3
from irods.message import Bad_AVU_Field
from irods.column import Like, NotLike


def normalize_to_bytes(string, unicode_encoding='utf8'):
    # Python2 and 3 enumerate bytestrings differently.
    ord_ = (lambda _:_) if any(x for x in string[:1] if type(x) is int) else ord
    if not string or ord_(max(x for x in string)) > 255:
        return string.encode(unicode_encoding)
    # str->bytes type conversion using element-wise copy, aka a trivial encode.
    array = bytearray(ord_(x) for x in string)
    return bytes(array)

def resolves_to_identical_bytestrings(avu1, avu2, key = normalize_to_bytes):
    avu1 = tuple(avu1)
    avu2 = tuple(avu2)
    if len(avu1) != len(avu2):
        return False
    for field1,field2 in zip(avu1,avu2):
        if key(field1) != key(field2):
            return False
    return True

class TestMeta(unittest.TestCase):
    '''Suite of tests on metadata operations
    '''
    # test metadata
    attr0, value0, unit0 = 'attr0', 'value0', 'unit0'
    attr1, value1, unit1 = 'attr1', 'value1', 'unit1'

    def test_stringtypes_in_general_query__issue_442(self):
        metadata = []
        value = u'a\u1000b'
        value_encoded = value.encode('utf8')
        contains_value = {type(value_encoded):b'%%'+value_encoded+b'%%',
                          type(value):'%%'+value+'%%'}
        for v in (value, value_encoded):

            # Establish invariant of exactly 2 AVUs attached to object.
            self.coll.metadata.remove_all()
            self.coll.metadata['a']=iRODSMeta('a',value)
            self.coll.metadata['b']=iRODSMeta('b','<arbitrary>')
            q = self.sess.query(CollectionMeta).filter(Collection.name == self.coll_path)
            self.assertEqual(len(list(q)),2)

            # Test query with operators Like and NotLike
            q = self.sess.query(CollectionMeta).filter(Collection.name == self.coll_path,
                                                       NotLike(CollectionMeta.value,contains_value[type(v)]))
            self.assertEqual(len(list(q)),1)
            q = self.sess.query(CollectionMeta).filter(Collection.name == self.coll_path,
                                                       Like(CollectionMeta.value,contains_value[type(v)]))
            self.assertEqual(len(list(q)),1)

            # Test query with operators == and !=
            q = self.sess.query(CollectionMeta).filter(Collection.name == self.coll_path, CollectionMeta.value == v)
            self.assertEqual(len(list(q)),1)
            q = self.sess.query(CollectionMeta).filter(Collection.name == self.coll_path, CollectionMeta.value != v)
            self.assertEqual(len(list(q)),1)
            metadata.append(self.coll.metadata['a'])

        # Test that application of unicode and bytestring metadata were equivalent
        self.assertEqual(metadata[0], metadata[1])

    @unittest.skipIf(PY3, 'Unicode strings are normal on Python3')
    def test_unicode_AVUs_in_Python2__issue_442(self):
        data_object = self.sess.data_objects.get(self.obj_path)
        meta_set = iRODSMeta(u'\u1000', u'value', u'units')
        meta_add = iRODSMeta(*tuple(meta_set))
        meta_add.name += u"-add"
        data_object.metadata.set(meta_set)
        data_object.metadata.add(meta_add)
        for index, meta in [(m.name, m) for m in (meta_add, meta_set)]:
            fetched = data_object.metadata[index]
            self.assertTrue(resolves_to_identical_bytestrings(fetched, meta), 'fetched unexpected meta for %r' % index)

    @unittest.skipIf(PY2, 'Byte strings are normal on Python2')
    def test_bytestring_AVUs_in_Python3__issue_442(self):
        data_object = self.sess.data_objects.get(self.obj_path)
        meta_set = iRODSMeta(u'\u1000'.encode('utf8'),b'value',b'units')
        meta_add = iRODSMeta(*tuple(meta_set))
        meta_add.name += b"-add"
        data_object.metadata.set(meta_set)
        data_object.metadata.add(meta_add)
        for index, meta in [(m.name, m) for m in (meta_add, meta_set)]:
            fetched = data_object.metadata[index]
            self.assertTrue(resolves_to_identical_bytestrings(fetched, meta), 'fetched unexpected meta for %r' % index)

    def setUp(self):
        self.sess = helpers.make_session()
        # test data
        self.coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)
        self.obj_name = 'test1'
        self.obj_path = '{coll_path}/{obj_name}'.format(**vars(self))

        # Create test collection and (empty) test object
        self.coll = self.sess.collections.create(self.coll_path)
        self.obj = self.sess.data_objects.create(self.obj_path)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        helpers.remove_unused_metadata(self.sess)
        self.sess.cleanup()

    from irods.test.helpers import create_simple_resc_hierarchy

    def test_atomic_metadata_operations_244(self):
        user = self.sess.users.get("rods")
        group = self.sess.groups.get("public")
        m = ( "attr_244","value","units")

        with self.assertRaises(BadAVUOperationValue):
            AVUOperation(operation="add", avu=m)

        with self.assertRaises(BadAVUOperationValue):
            AVUOperation(operation="not_add_or_remove", avu=iRODSMeta(*m))

        with self.assertRaises(BadAVUOperationKeyword):
            AVUOperation(operation="add", avu=iRODSMeta(*m), extra_keyword=None)


        with self.assertRaises(InvalidAtomicAVURequest):
            user.metadata.apply_atomic_operations( tuple() )

        user.metadata.apply_atomic_operations()   # no AVUs applied - no-op without error

        for n,obj in enumerate((group, user, self.coll, self.obj)):
            avus = [ iRODSMeta('some_attribute',str(i),'some_units') for i in range(n*100,(n+1)*100) ]
            obj.metadata.apply_atomic_operations(*[AVUOperation(operation="add", avu=avu_) for avu_ in avus])
            obj.metadata.apply_atomic_operations(*[AVUOperation(operation="remove", avu=avu_) for avu_ in avus])


    def test_atomic_metadata_operation_for_resource_244(self):
        (root,leaf)=('ptX','rescX')
        with self.create_simple_resc_hierarchy(root,leaf):
            root_resc = self.sess.resources.get(root)   # resource objects
            leaf_resc = self.sess.resources.get(leaf)
            root_tuple = ('role','root','new units #1')    # AVU tuples to apply
            leaf_tuple = ('role','leaf','new units #2')
            root_resc.metadata.add( *root_tuple[:2] ) # first apply without units ...
            leaf_resc.metadata.add( *leaf_tuple[:2] )
            for resc,resc_tuple in ((root_resc, root_tuple), (leaf_resc, leaf_tuple)):
                resc.metadata.apply_atomic_operations(  # metadata set operation (remove + add) to add units
                    AVUOperation(operation="remove", avu=iRODSMeta(*resc_tuple[:2])),
                    AVUOperation(operation="add", avu=iRODSMeta(*resc_tuple[:3]))
                )
                resc_meta = self.sess.metadata.get(Resource, resc.name)
                avus_to_tuples = lambda avu_list: sorted([(i.name,i.value,i.units) for i in avu_list])
                self.assertEqual(avus_to_tuples(resc_meta), avus_to_tuples([iRODSMeta(*resc_tuple)]))


    def test_atomic_metadata_operation_for_data_object_244(self):
        AVUs_Equal = lambda avu1,avu2,fn=(lambda x:x): fn(avu1)==fn(avu2)
        AVU_As_Tuple = lambda avu,length=3:(avu.name,avu.value,avu.units)[:length]
        AVU_Units_String = lambda avu:"" if not avu.units else avu.units
        m = iRODSMeta( "attr_244","value","units")
        self.obj.metadata.add(m)
        meta = self.sess.metadata.get(DataObject, self.obj_path)
        self.assertEqual(len(meta), 1)
        self.assertTrue(AVUs_Equal(m,meta[0],AVU_As_Tuple))
        self.obj.metadata.apply_atomic_operations(                                  # remove original AVU and replace
           AVUOperation(operation="remove",avu=m),                                  #   with two altered versions
           AVUOperation(operation="add",avu=iRODSMeta(m.name,m.value,"units_244")), # (one of them without units) ...
           AVUOperation(operation="add",avu=iRODSMeta(m.name,m.value))
        )
        meta = self.sess.metadata.get(DataObject, self.obj_path)   # ... check integrity of change
        self.assertEqual(sorted([AVU_Units_String(i) for i in meta]), ["","units_244"])

    def test_atomic_metadata_operations_255(self):
        my_resc = self.sess.resources.create('dummyResc','passthru')
        avus = [iRODSMeta('a','b','c'), iRODSMeta('d','e','f')]
        objects = [ self.sess.users.get("rods"), self.sess.groups.get("public"), my_resc,
                    self.sess.collections.get(self.coll_path), self.sess.data_objects.get(self.obj_path)  ]
        try:
            for obj in objects:
                self.assertEqual(len(obj.metadata.items()), 0)
                for n,item in enumerate(avus):
                    obj.metadata.apply_atomic_operations(AVUOperation(operation='add',avu=item))
                    self.assertEqual(len(obj.metadata.items()), n+1)
        finally:
            for obj in objects: obj.metadata.remove_all()
            my_resc.remove()

    def test_get_obj_meta(self):
        # get object metadata
        meta = self.sess.metadata.get(DataObject, self.obj_path)

        # there should be no metadata at this point
        assert len(meta) == 0

    def test_resc_meta(self):
        rescname = 'demoResc'
        self.sess.resources.get(rescname).metadata.remove_all()
        self.sess.metadata.set(Resource, rescname, iRODSMeta('zero','marginal','cost'))
        self.sess.metadata.add(Resource, rescname, iRODSMeta('zero','marginal'))
        self.sess.metadata.set(Resource, rescname, iRODSMeta('for','ever','after'))
        meta = self.sess.resources.get(rescname).metadata
        self.assertTrue( len(meta) == 3 )
        resource = self.sess.resources.get(rescname)
        all_AVUs= resource.metadata.items()
        for avu in all_AVUs:
            resource.metadata.remove(avu)
        self.assertTrue(0 == len(self.sess.resources.get(rescname).metadata))

    def test_add_obj_meta(self):
        # add metadata to test object
        self.sess.metadata.add(DataObject, self.obj_path,
                               iRODSMeta(self.attr0, self.value0))
        self.sess.metadata.add(DataObject, self.obj_path,
                               iRODSMeta(self.attr1, self.value1, self.unit1))

        # Throw in some unicode for good measure
        attribute, value = 'attr2', u'☭⛷★⚽'
        self.sess.metadata.add(DataObject, self.obj_path,
                               iRODSMeta(attribute, value))

        # get object metadata
        meta = self.sess.metadata.get(DataObject, self.obj_path)

        # sort results by metadata id
        def getKey(AVU):
            return AVU.avu_id
        meta = sorted(meta, key=getKey)

        # assertions
        assert meta[0].name == self.attr0
        assert meta[0].value == self.value0

        assert meta[1].name == self.attr1
        assert meta[1].value == self.value1
        assert meta[1].units == self.unit1

        assert meta[2].name == attribute
        testValue = (value if PY3 else value.encode('utf8'))
        assert meta[2].value == testValue


    def test_add_obj_meta_empty(self):
        '''Should raise exception
        '''

        # try to add metadata with empty value
        with self.assertRaises(ValueError):
            self.sess.metadata.add(DataObject, self.obj_path,
                                   iRODSMeta('attr_with_empty_value', ''))


    def test_copy_obj_meta(self):
        # test destination object for copy
        dest_obj_path = self.coll_path + '/test2'
        self.sess.data_objects.create(dest_obj_path)

        # add metadata to test object
        self.sess.metadata.add(DataObject, self.obj_path,
                               iRODSMeta(self.attr0, self.value0))

        # copy metadata
        self.sess.metadata.copy(
            DataObject, DataObject, self.obj_path, dest_obj_path)

        # get destination object metadata
        dest_meta = self.sess.metadata.get(DataObject, dest_obj_path)

        # check metadata
        assert dest_meta[0].name == self.attr0


    def test_remove_obj_meta(self):
        # add metadata to test object
        self.sess.metadata.add(DataObject, self.obj_path,
                               iRODSMeta(self.attr0, self.value0))

        # check that metadata is there
        meta = self.sess.metadata.get(DataObject, self.obj_path)
        assert meta[0].name == self.attr0

        # remove metadata from object
        self.sess.metadata.remove(DataObject, self.obj_path,
                                  iRODSMeta(self.attr0, self.value0))

        # check that metadata is gone
        meta = self.sess.metadata.get(DataObject, self.obj_path)
        assert len(meta) == 0


    def test_metadata_manipulations_with_admin_kw__364__365(self):
        try:
            d = user = None
            adm = self.sess

            if adm.server_version <= (4,2,11):
                self.skipTest('ADMIN_KW not valid for Metadata API in iRODS 4.2.11 and previous')

            # Create a rodsuser, and a session for that roduser.
            user = adm.users.create ( 'bobby','rodsuser' )
            user.modify('password','bpass')
            with iRODSSession (port=adm.port,zone=adm.zone,host=adm.host, user=user.name,password='bpass') as ses:
                # Create a data object owned by the rodsuser.  Set AVUs in various ways and guarantee each attempt
                # has the desired effect.
                d = ses.data_objects.create('/{adm.zone}/home/{user.name}/testfile'.format(**locals()))

                d.metadata.set('a','aa','1')
                self.assertIn(('a','aa','1'), d.metadata.items())

                d.metadata.set('a','aa')
                self.assertEqual([('a','aa')], [tuple(_) for _ in d.metadata.items()])

                d.metadata['a'] = iRODSMeta('a','bb')
                self.assertEqual([('a','bb')], [tuple(_) for _ in d.metadata.items()])

                # Now the admin does two AVU-set operations.  A successful test of these operations' success
                # includes that both ('x','y') has been added and ('a','b','c') has overwritten ('a','bb').

                da = adm.data_objects.get(d.path)
                da.metadata.set('a','b','c',**{kw.ADMIN_KW:''})
                da.metadata(admin = True)['x'] = iRODSMeta('x','y')
                d = ses.data_objects.get(d.path) # assure metadata are not cached
                self.assertEqual(set([('x','y'), ('a','b','c')]),
                                 set(tuple(_) for _ in d.metadata.items()))
        finally:
            if d: d.unlink(force=True)
            if user: user.remove()


    def test_add_coll_meta(self):
        # add metadata to test collection
        self.sess.metadata.add(Collection, self.coll_path,
                               iRODSMeta(self.attr0, self.value0))

        # get collection metadata
        meta = self.sess.metadata.get(Collection, self.coll_path)

        # assertions
        assert meta[0].name == self.attr0
        assert meta[0].value == self.value0

        # remove collection metadata
        self.sess.metadata.remove(Collection, self.coll_path,
                                  iRODSMeta(self.attr0, self.value0))

        # check that metadata is gone
        meta = self.sess.metadata.get(Collection, self.coll_path)
        assert len(meta) == 0


    def test_meta_repr(self):
        # test obj
        collection = self.coll_path
        filename = 'test_meta_repr.txt'
        test_obj_path = '{collection}/{filename}'.format(**locals())

        # make object
        obj = helpers.make_object(self.sess, test_obj_path)

        # test AVU
        attribute, value, units = ('test_attr', 'test_value', 'test_units')

        # add metadata to test object
        meta = self.sess.metadata.add(DataObject, test_obj_path,
                                      iRODSMeta(attribute, value, units))

        # get metadata
        meta = self.sess.metadata.get(DataObject, test_obj_path)
        avu_id = meta[0].avu_id

        # assert
        self.assertEqual(
            repr(meta[0]), "<iRODSMeta {avu_id} {attribute} {value} {units}>".format(**locals()))

        # remove test object
        obj.unlink(force=True)


    def test_irodsmetacollection_data_obj(self):
        '''
        Tested as data_object metadata
        '''
        # test settings
        avu_count = 5

        # make test object
        test_obj_path = self.coll_path + '/test_irodsmetacollection'
        test_obj = helpers.make_object(self.sess, test_obj_path)

        # test AVUs
        triplets = [('test_attr' + str(i), 'test_value', 'test_units')
                    for i in range(avu_count)]

        # get coll meta
        imc = test_obj.metadata

        # try invalid key
        with self.assertRaises(KeyError):
            imc.get_one('bad_key')

        # invalid key type
        with self.assertRaises(TypeError):
            imc.get_one(list())

        # try empty update values
        with self.assertRaises(ValueError):
            imc.add()

        # add AVUs
        for triplet in triplets:
            imc.add(*triplet)

        # add another AVU with existing attribute name
        attr_name = triplets[0][0]
        duplicate_triplet = (attr_name, 'other_value', 'test_units')
        imc.add(*duplicate_triplet)

        # get_one should fail
        with self.assertRaises(KeyError):
            imc.get_one(attr_name)

        # remove triplet
        imc.remove(*duplicate_triplet)
        imc.get_one(attr_name)

        # get keys
        for key in imc.keys():
            self.assertIn(key, [triplet[0] for triplet in triplets])

        # get items
        for avu in imc.items():
            self.assertIsInstance(avu, iRODSMeta)
            self.assertIn(avu.name, [triplet[0] for triplet in triplets])
            self.assertIn(avu.value, [triplet[1] for triplet in triplets])
            self.assertIn(avu.units, [triplet[2] for triplet in triplets])

        # try contains
        self.assertIn(triplets[0][0], imc)

        # try contains with bad key type
        with self.assertRaises(TypeError):
            _ = (int() in imc)

        # set item
        imc[attr_name] = iRODSMeta(attr_name, 'boo')

        # get item
        _ = imc[attr_name]

        # del item with bad key type
        with self.assertRaises(TypeError):
            del imc[int()]

        # del item
        del imc[attr_name]

        with self.assertRaises(KeyError):
            _ = imc[attr_name]

        # remove all metadta
        imc.remove_all()
        self.assertEqual(len(imc), 0)

        # remove test collection
        test_obj.unlink(force=True)


    @staticmethod
    def check_timestamps(metadata_accessor, key):
        avu = metadata_accessor[key]
        create = getattr(avu,'create_time',None)
        modify = getattr(avu,'modify_time',None)
        return (create,modify)


    def test_timestamp_access_386(self):
        with helpers.make_session() as session:
            def units():
                return str(time.time())
            d = None
            try:
                d = session.data_objects.create('/tempZone/home/rods/issue_386')

                # Test metadata access without timestamps

                meta = d.metadata
                avu = iRODSMeta('no_ts','val',units())
                meta.set(avu)
                self.assertEqual((None, None),		# Assert no timestamps are stored.
                                 self.check_timestamps(meta, key = avu.name))

                # -- Test metadata access with timestamps

                meta_ts = meta(timestamps = True)
                avu_use_ts = iRODSMeta('use_ts','val',units())
                meta_ts.set(avu_use_ts)
                time.sleep(1.5)
                now = datetime.datetime.utcnow()
                time.sleep(1.5)
                avu_use_ts.units = units()
                meta_ts.set(avu_use_ts)			# Set an AVU with modified units.

                (create, modify) = self.check_timestamps(meta_ts, key = avu_use_ts.name)

                self.assertLess(create, now)		#  Ensure timestamps are in proper order.
                self.assertLess(now, modify)
            finally:
                if d: d.unlink(force = True)
                helpers.remove_unused_metadata(session)

    def test_nonstring_as_AVU_value_raises_an_error__issue_434(self):
        with self.assertRaisesRegexp(Bad_AVU_Field,'incorrect type'):
            self.coll.metadata.set("an_attribute",0)

    def test_empty_string_as_AVU_value_raises_an_error__issue_434(self):
        with self.assertRaisesRegexp(Bad_AVU_Field,'zero-length'):
            self.coll.metadata.set("an_attribute","")

if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
