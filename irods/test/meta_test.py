#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys
import unittest
from irods.meta import (iRODSMeta, AVUOperation, BadAVUOperationValue, BadAVUOperationKeyword)
from irods.manager.metadata_manager import InvalidAtomicAVURequest
from irods.models import (DataObject, Collection, Resource)
import irods.test.helpers as helpers
from six.moves import range


class TestMeta(unittest.TestCase):
    '''Suite of tests on metadata operations
    '''
    # test metadata
    attr0, value0, unit0 = 'attr0', 'value0', 'unit0'
    attr1, value1, unit1 = 'attr1', 'value1', 'unit1'

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
        group = self.sess.user_groups.get("public")
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
        objects = [ self.sess.users.get("rods"), self.sess.user_groups.get("public"), my_resc,
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
        assert meta[2].value == value


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


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
