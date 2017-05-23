#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import socket
import unittest
from irods.models import Collection, DataObject
from irods.exception import DataObjectDoesNotExist, CollectionDoesNotExist
from irods.column import Criterion
import irods.test.config as config
import irods.test.helpers as helpers
import json
import hashlib
import base64
import irods.keywords as kw

class TestDataObjOps(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session_from_config()

        # get server version
        with self.sess.pool.get_connection() as conn:
            self.server_version = tuple(int(token)
                                        for token in conn.server_version.replace('rods', '').split('.'))

        # Create test collection
        self.coll_path = '/{0}/home/{1}/test_dir'.format(
            config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
        self.coll = helpers.make_collection(self.sess, self.coll_path)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def make_new_server_config_json(self, server_config_filename):
        # load server_config.json to inject a new rule base
        with open(server_config_filename) as f:
            svr_cfg = json.load(f)

        # inject a new rule base into the native rule engine
        svr_cfg['plugin_configuration']['rule_engines'][0]['plugin_specific_configuration'][
            're_rulebase_set'] = ["test",  "core"]

        # dump to a string to repave the existing server_config.json
        return json.dumps(svr_cfg, sort_keys=True, indent=4, separators=(',', ': '))

    def test_rename_obj(self):
        # test args
        collection = self.coll_path
        old_name = 'foo'
        new_name = 'bar'

        # make object in test collection
        path = "{collection}/{old_name}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # for coverage
        repr(obj)
        for replica in obj.replicas:
            repr(replica)

        # get object id
        saved_id = obj.id

        # rename object
        new_path = "{collection}/{new_name}".format(**locals())
        self.sess.data_objects.move(path, new_path)

        # get updated object
        obj = self.sess.data_objects.get(new_path)

        # compare ids
        self.assertEqual(obj.id, saved_id)

        # remove object
        self.sess.data_objects.unlink(new_path)

    def test_move_obj_to_coll(self):
        # test args
        collection = self.coll_path
        new_coll_name = 'my_coll'
        file_name = 'foo'

        # make object in test collection
        path = "{collection}/{file_name}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object id
        saved_id = obj.id

        # make new collection and move object to it
        new_coll_path = "{collection}/{new_coll_name}".format(**locals())
        new_coll = helpers.make_collection(self.sess, new_coll_path)
        self.sess.data_objects.move(path, new_coll_path)

        # get new object id
        new_path = "{collection}/{new_coll_name}/{file_name}".format(
            **locals())
        obj = self.sess.data_objects.get(new_path)

        # compare ids
        self.assertEqual(obj.id, saved_id)

        # remove new collection
        new_coll.remove(recurse=True, force=True)

    def test_copy_obj_to_obj(self):
        # test args
        collection = self.coll_path
        src_file_name = 'foo'
        dest_file_name = 'bar'

        # make object in test collection
        src_path = "{collection}/{src_file_name}".format(**locals())
        src_obj = helpers.make_object(self.sess, src_path, options={kw.REG_CHKSUM_KW: ''})

        # copy object
        options = {kw.VERIFY_CHKSUM_KW: ''}
        dest_path = "{collection}/{dest_file_name}".format(**locals())
        self.sess.data_objects.copy(src_path, dest_path, options)

        # compare checksums
        dest_obj = self.sess.data_objects.get(dest_path)
        self.assertEqual(src_obj.checksum, dest_obj.checksum)

    def test_copy_obj_to_coll(self):
        # test args
        collection = self.coll_path
        file_name = 'foo'
        dest_coll_name = 'copy_dest_coll'
        dest_coll_path = "{collection}/{dest_coll_name}".format(**locals())
        dest_obj_path = "{collection}/{dest_coll_name}/{file_name}".format(
            **locals())

        # make object in test collection
        path = "{collection}/{file_name}".format(**locals())
        src_obj = helpers.make_object(self.sess, path, options={kw.REG_CHKSUM_KW: ''})

        # make new collection and copy object into it
        options = {kw.VERIFY_CHKSUM_KW: ''}
        helpers.make_collection(self.sess, dest_coll_path)
        self.sess.data_objects.copy(path, dest_coll_path, options)

        # compare checksums
        dest_obj = self.sess.data_objects.get(dest_obj_path)
        self.assertEqual(src_obj.checksum, dest_obj.checksum)

    def test_invalid_get(self):
        # bad paths
        path_with_invalid_file = self.coll_path + '/hamsalad'
        path_with_invalid_coll = self.coll_path + '/hamsandwich/foo'

        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(path_with_invalid_file)

        with self.assertRaises(CollectionDoesNotExist):
            obj = self.sess.data_objects.get(path_with_invalid_coll)

    def test_force_unlink(self):
        collection = self.coll_path
        filename = 'test_force_unlink.txt'
        file_path = '{collection}/{filename}'.format(**locals())

        # make object
        obj = helpers.make_object(self.sess, file_path)

        # force remove object
        obj.unlink(force=True)

        # should be gone
        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(file_path)

        # make sure it's not in the trash either
        conditions = [DataObject.name == filename,
                      Criterion('like', Collection.name, "/dev/trash/%%")]
        query = self.sess.query(
            DataObject.id, DataObject.name, Collection.name).filter(*conditions)
        results = query.all()
        self.assertEqual(len(results), 0)

    def test_obj_truncate(self):
        collection = self.coll_path
        filename = 'test_obj_truncate.txt'
        file_path = '{collection}/{filename}'.format(**locals())
        # random long content
        content = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
        truncated_content = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        # make object
        obj = helpers.make_object(self.sess, file_path, content=content)

        # truncate object
        obj.truncate(len(truncated_content))

        # read file
        obj = self.sess.data_objects.get(file_path)
        with obj.open('r') as f:
            self.assertEqual(f.read().decode(), truncated_content)

    def test_multiple_reads(self):
        collection = self.coll_path

        # make files
        filenames = []
        for filename in ['foo', 'bar', 'baz']:
            path = '{collection}/{filename}'.format(**locals())
            helpers.make_object(self.sess, path=path, content=path)
            filenames.append(path)

        # read files
        for filename in filenames:
            obj = self.sess.data_objects.get(filename)
            with obj.open('r') as f:
                self.assertEqual(f.read().decode(), obj.path)

    @unittest.skipIf(
        config.IRODS_SERVER_HOST != 'localhost' and config.IRODS_SERVER_HOST != socket.gethostname(
        ), "Cannot modify remote server configuration")
    def test_create_with_checksum(self):
        # skip if server is older than 4.2
        if self.server_version < (4, 2, 0):
            self.skipTest('Expects iRODS 4.2 server-side configuration')

        # server config
        server_config_dir = '/etc/irods'
        test_re_file = os.path.join(server_config_dir, 'test.re')
        server_config_file = os.path.join(
            server_config_dir, 'server_config.json')

        try:
            with helpers.file_backed_up(server_config_file):
                # make pep rule
                test_rule = "acPostProcForPut { msiDataObjChksum ($objPath, 'forceChksum=', *out )}"

                # write pep rule into test_re
                with open(test_re_file, 'w') as f:
                    f.write(test_rule)

                # make new server configuration with additional re file
                new_server_config = self.make_new_server_config_json(
                    server_config_file)

                # repave the existing server_config.json to add test_re
                with open(server_config_file, 'w') as f:
                    f.write(new_server_config)

                # must make a new connection for the agent to pick up the
                # updated configuration
                self.sess.cleanup()

                # test object
                collection = self.coll_path
                filename = 'checksum_test_file'
                obj_path = "{collection}/{filename}".format(**locals())
                contents = 'blah' * 100
                checksum = base64.b64encode(
                    hashlib.sha256(contents).digest()).decode()

                # make object in test collection
                options = {kw.OPR_TYPE_KW: 1}   # PUT_OPR
                obj = helpers.make_object(self.sess, obj_path, content=contents, options=options)

                # verify object's checksum
                self.assertEqual(
                    obj.checksum, "sha2:{checksum}".format(**locals()))

                # cleanup
                os.unlink(test_re_file)

        except IOError as e:
            # a likely fail scenario
            if e.errno == 13:
                self.skipTest("No permission to modify server configuration")
            raise
        except:
            raise


    def test_open_file_with_options(self):
        '''
        Similar to checksum test above,
        except that we use an optional keyword on open
        instead of a PEP.
        '''

        # skip if server is 4.1.4 or older
        if self.server_version <= (4, 1, 4):
            self.skipTest('Not supported')

        # test data
        collection = self.coll_path
        filename = 'test_open_file_with_options.txt'
        file_path = '/tmp/{filename}'.format(**locals())
        obj_path = '{collection}/{filename}'.format(**locals())
        contents = u"blah blah " * 10000
        checksum = base64.b64encode(hashlib.sha256(contents.encode('utf-8')).digest()).decode()

        objs = self.sess.data_objects

        # make test file
        with open(file_path, 'w') as f:
            f.write(contents)

        # options for open/close
        options = {kw.REG_CHKSUM_KW: ''}

        # write contents of file to object
        with open(file_path, 'rb') as f, objs.open(obj_path, 'w', options) as o:
            for chunk in helpers.chunks(f):
                o.write(chunk)

        # update object and verify checksum
        obj = self.sess.data_objects.get(obj_path)
        self.assertEqual(obj.checksum, "sha2:{checksum}".format(**locals()))

        # cleanup
        obj.unlink(force=True)
        os.unlink(file_path)


    def test_obj_replicate(self):
        # test data
        resc_name = 'temporary_test_resource'
        if config.IRODS_SERVER_VERSION < (4, 0, 0):
            resc_type = 'unix file system'
            resc_class = 'cache'
        else:
            resc_type = 'unixfilesystem'
            resc_class = ''
        resc_host = config.IRODS_SERVER_HOST  # use remote host when available in CI
        resc_path = '/tmp/' + resc_name

        # make second resource
        self.sess.resources.create(
            resc_name, resc_type, resc_host, resc_path, resource_class=resc_class)

        # make test object on default resource
        collection = self.coll_path
        filename = 'test_replicate.txt'
        file_path = '{collection}/{filename}'.format(**locals())
        obj = helpers.make_object(self.sess, file_path)

        # replicate object to 2nd resource
        obj.replicate(resc_name)

        # refresh object
        obj = self.sess.data_objects.get(obj.path)

        # check that object is on both resources
        resources = [replica.resource_name for replica in obj.replicas]
        self.assertEqual(len(resources), 2)
        self.assertIn(resc_name, resources)

        # force remove object
        obj.unlink(force=True)

        # delete second resource
        self.sess.resources.remove(resc_name)


    @unittest.skipIf(config.IRODS_SERVER_VERSION < (4, 0, 0), "iRODS 4+")
    def test_replica_number(self):
        session = self.sess
        zone = session.zone
        username = session.username
        obj_path = '/{zone}/home/{username}/foo.txt'.format(**locals())
        obj_content = b'blah'
        number_of_replicas = 7

        # make replication resource
        replication_resource = session.resources.create('repl_resc', 'replication')

        # make ufs resources
        ufs_resources = []
        for i in range(number_of_replicas):
            resource_name = 'ufs{0}'.format(i)
            resource_type = 'unixfilesystem'
            resource_host = session.host
            resource_path = '/tmp/' + resource_name
            ufs_resources.append(session.resources.create(
                resource_name, resource_type, resource_host, resource_path))

            # add child to replication resource
            session.resources.add_child(replication_resource.name, resource_name)

        # create object on replication resource
        obj = session.data_objects.create(obj_path, replication_resource.name)

        # write to object
        with obj.open('w+') as obj_desc:
            obj_desc.write(obj_content)

        # refresh object
        obj = session.data_objects.get(obj_path)

        # assertions on replicas
        self.assertEqual(len(obj.replicas), number_of_replicas)
        for i, replica in enumerate(obj.replicas):
            self.assertEqual(replica.number, i)

        # now trim odd-numbered replicas
        for i in [1, 3, 5]:
            options = {}
            options[kw.REPL_NUM_KW] = str(i)
            obj.unlink(options=options)

        # refresh object
        obj = session.data_objects.get(obj_path)

        # check remaining replica numbers
        replica_numbers = []
        for replica in obj.replicas:
            replica_numbers.append(replica.number)
        self.assertEqual(replica_numbers, [0, 2, 4, 6])

        # remove object
        obj.unlink(force=True)

        # remove ufs resources
        for resource in ufs_resources:
            session.resources.remove_child(replication_resource.name, resource.name)
            resource.remove()

        # remove replication resource
        replication_resource.remove()


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
