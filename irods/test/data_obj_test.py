#! /usr/bin/env python
from __future__ import absolute_import
import os
import sys
import socket
import json
import hashlib
import base64
import random
import string
import unittest
from irods.models import Collection, DataObject
from irods.session import iRODSSession
import irods.exception as ex
from irods.column import Criterion
from irods.data_object import chunks
import irods.test.helpers as helpers
import irods.keywords as kw
from datetime import datetime

class TestDataObjOps(unittest.TestCase):

    def setUp(self):
        self.sess = helpers.make_session()

        # Create test collection
        self.coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)
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


    def sha256_checksum(self, filename, block_size=65536):
        sha256 = hashlib.sha256()
        with open(filename, 'rb') as f:
            for chunk in chunks(f, block_size):
                sha256.update(chunk)
        return sha256.hexdigest()


    def test_obj_exists(self):
        obj_name = 'this_object_will_exist_once_made'
        exists_path = '{}/{}'.format(self.coll_path, obj_name)
        helpers.make_object(self.sess, exists_path)
        self.assertTrue(self.sess.data_objects.exists(exists_path))


    def test_obj_does_not_exist(self):
        does_not_exist_name = 'this_object_will_never_exist'
        does_not_exist_path = '{}/{}'.format(self.coll_path,
                                             does_not_exist_name)
        self.assertFalse(self.sess.data_objects.exists(does_not_exist_path))


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

    def test_copy_existing_obj_to_relative_dest_fails_irods4796(self):
        if self.sess.server_version <= (4, 2, 7):
            self.skipTest('iRODS servers <= 4.2.7 will give nondescriptive error')
        obj_name = 'this_object_will_exist_once_made'
        exists_path = '{}/{}'.format(self.coll_path, obj_name)
        helpers.make_object(self.sess, exists_path)
        self.assertTrue(self.sess.data_objects.exists(exists_path))
        non_existing_zone = 'this_zone_absent'
        relative_dst_path = '{non_existing_zone}/{obj_name}'.format(**locals())
        options = {}
        with self.assertRaises(ex.USER_INPUT_PATH_ERR):
            self.sess.data_objects.copy(exists_path, relative_dst_path, **options)

    def test_copy_from_nonexistent_absolute_data_obj_path_fails_irods4796(self):
        if self.sess.server_version <= (4, 2, 7):
            self.skipTest('iRODS servers <= 4.2.7 will hang the client')
        non_existing_zone = 'this_zone_absent'
        src_path = '/{non_existing_zone}/non_existing.src'.format(**locals())
        dst_path = '/{non_existing_zone}/non_existing.dst'.format(**locals())
        options = {}
        with self.assertRaises(ex.USER_INPUT_PATH_ERR):
            self.sess.data_objects.copy(src_path, dst_path, **options)

    def test_copy_from_relative_path_fails_irods4796(self):
        if self.sess.server_version <= (4, 2, 7):
            self.skipTest('iRODS servers <= 4.2.7 will hang the client')
        src_path = 'non_existing.src'
        dst_path = 'non_existing.dst'
        options = {}
        with self.assertRaises(ex.USER_INPUT_PATH_ERR):
            self.sess.data_objects.copy(src_path, dst_path, **options)

    def test_copy_obj_to_obj(self):
        # test args
        collection = self.coll_path
        src_file_name = 'foo'
        dest_file_name = 'bar'

        # make object in test collection
        options={kw.REG_CHKSUM_KW: ''}
        src_path = "{collection}/{src_file_name}".format(**locals())
        src_obj = helpers.make_object(self.sess, src_path, **options)

        # copy object
        options = {kw.VERIFY_CHKSUM_KW: ''}
        dest_path = "{collection}/{dest_file_name}".format(**locals())
        self.sess.data_objects.copy(src_path, dest_path, **options)

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
        options={kw.REG_CHKSUM_KW: ''}
        src_obj = helpers.make_object(self.sess, path, **options)

        # make new collection and copy object into it
        options = {kw.VERIFY_CHKSUM_KW: ''}
        helpers.make_collection(self.sess, dest_coll_path)
        self.sess.data_objects.copy(path, dest_coll_path, **options)

        # compare checksums
        dest_obj = self.sess.data_objects.get(dest_obj_path)
        self.assertEqual(src_obj.checksum, dest_obj.checksum)


    def test_invalid_get(self):
        # bad paths
        path_with_invalid_file = self.coll_path + '/hamsalad'
        path_with_invalid_coll = self.coll_path + '/hamsandwich/foo'

        with self.assertRaises(ex.DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(path_with_invalid_file)

        with self.assertRaises(ex.CollectionDoesNotExist):
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
        with self.assertRaises(ex.DataObjectDoesNotExist):
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


    def test_create_with_checksum(self):
        # skip if server is remote
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # skip if server is older than 4.2
        if self.sess.server_version < (4, 2, 0):
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
                    hashlib.sha256(contents.encode()).digest()).decode()

                # make object in test collection
                options = {kw.OPR_TYPE_KW: 1}   # PUT_OPR
                obj = helpers.make_object(self.sess, obj_path, content=contents, **options)

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


    def test_put_file_trigger_pep(self):
        # skip if server is remote
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # skip if server is older than 4.2
        if self.sess.server_version < (4, 2, 0):
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

                # make pseudo-random test file
                filename = 'test_put_file_trigger_pep.txt'
                test_file = os.path.join('/tmp', filename)
                contents = ''.join(random.choice(string.printable) for _ in range(1024)).encode()
                contents = contents[:1024]
                with open(test_file, 'wb') as f:
                    f.write(contents)

                # compute test file's checksum
                checksum = base64.b64encode(hashlib.sha256(contents).digest()).decode()

                # put object in test collection
                collection = self.coll.path
                self.sess.data_objects.put(test_file, '{collection}/'.format(**locals()))

                # get object to confirm checksum
                obj = self.sess.data_objects.get('{collection}/{filename}'.format(**locals()))

                # verify object's checksum
                self.assertEqual(obj.checksum, "sha2:{checksum}".format(**locals()))

                # cleanup
                os.unlink(test_re_file)
                os.unlink(test_file)

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
        if self.sess.server_version <= (4, 1, 4):
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
        with open(file_path, 'rb') as f, objs.open(obj_path, 'w', **options) as o:
            for chunk in chunks(f):
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
        if self.sess.server_version < (4, 0, 0):
            resc_type = 'unix file system'
            resc_class = 'cache'
        else:
            resc_type = 'unixfilesystem'
            resc_class = ''
        resc_host = self.sess.host  # use remote host when available in CI
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


    def test_replica_number(self):
        if self.sess.server_version < (4, 0, 0):
            self.skipTest('For iRODS 4+')

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
            resource_name = 'ufs{}'.format(i)
            resource_type = 'unixfilesystem'
            resource_host = session.host
            resource_path = '/tmp/' + resource_name
            ufs_resources.append(session.resources.create(
                resource_name, resource_type, resource_host, resource_path))

            # add child to replication resource
            session.resources.add_child(replication_resource.name, resource_name)

        # make test object on replication resource
        if self.sess.server_version > (4, 1, 4):
            # skip create
            options = {kw.DEST_RESC_NAME_KW: replication_resource.name}
            with session.data_objects.open(obj_path, 'w', **options) as obj:
                obj.write(obj_content)

        else:
            # create object on replication resource
            obj = session.data_objects.create(obj_path, replication_resource.name)

            # write to object
            with obj.open('w') as obj_desc:
                obj_desc.write(obj_content)

        # refresh object
        obj = session.data_objects.get(obj_path)

        # assertions on replicas
        self.assertEqual(len(obj.replicas), number_of_replicas)
        for i, replica in enumerate(obj.replicas):
            self.assertEqual(replica.number, i)

        # now trim odd-numbered replicas
        for i in [1, 3, 5]:
            options = {kw.REPL_NUM_KW: str(i)}
            obj.unlink(**options)

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


    def test_repave_replicas(self):
        # Can't do one step open/create with older servers
        if self.sess.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        number_of_replicas = 7
        session = self.sess
        zone = session.zone
        username = session.username
        test_dir = '/tmp'
        filename = 'repave_replica_test_file.txt'
        test_file = os.path.join(test_dir, filename)
        obj_path = '/{zone}/home/{username}/{filename}'.format(**locals())

        # make test file
        obj_content = u'foobar'
        checksum = base64.b64encode(hashlib.sha256(obj_content.encode('utf-8')).digest()).decode()
        with open(test_file, 'w') as f:
            f.write(obj_content)

        # put test file onto default resource
        options = {kw.REG_CHKSUM_KW: ''}
        session.data_objects.put(test_file, obj_path, **options)

        # make ufs resources and replicate object
        ufs_resources = []
        for i in range(number_of_replicas):
            resource_name = 'ufs{}'.format(i)
            resource_type = 'unixfilesystem'
            resource_host = session.host
            resource_path = '/tmp/{}'.format(resource_name)
            ufs_resources.append(session.resources.create(
                resource_name, resource_type, resource_host, resource_path))

            session.data_objects.replicate(obj_path, resource=resource_name)

        # refresh object
        obj = session.data_objects.get(obj_path)

        # verify each replica's checksum
        for replica in obj.replicas:
            self.assertEqual(replica.checksum, 'sha2:{}'.format(checksum))

        # now repave test file
        obj_content = u'bar'
        checksum = base64.b64encode(hashlib.sha256(obj_content.encode('utf-8')).digest()).decode()
        with open(test_file, 'w') as f:
            f.write(obj_content)

        # update all replicas
        options = {kw.REG_CHKSUM_KW: '', kw.ALL_KW: ''}
        session.data_objects.put(test_file, obj_path, **options)
        obj = session.data_objects.get(obj_path)

        # verify each replica's checksum
        for replica in obj.replicas:
            self.assertEqual(replica.checksum, 'sha2:{}'.format(checksum))

        # remove object
        obj.unlink(force=True)

        # remove ufs resources
        for resource in ufs_resources:
            resource.remove()

    def test_get_replica_size(self):
        session = self.sess

        # Can't do one step open/create with older servers
        if session.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        # test vars
        test_dir = '/tmp'
        filename = 'get_replica_size_test_file'
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path

        # make random 16byte binary file
        original_size = 16
        with open(test_file, 'wb') as f:
            f.write(os.urandom(original_size))

        # make ufs resources
        ufs_resources = []
        for i in range(2):
            resource_name = 'ufs{}'.format(i)
            resource_type = 'unixfilesystem'
            resource_host = session.host
            resource_path = '/tmp/{}'.format(resource_name)
            ufs_resources.append(session.resources.create(
                resource_name, resource_type, resource_host, resource_path))

        # put file in test collection and replicate
        obj_path = '{collection}/{filename}'.format(**locals())
        options = {kw.DEST_RESC_NAME_KW: ufs_resources[0].name}
        session.data_objects.put(test_file, collection + '/', **options)
        session.data_objects.replicate(obj_path, ufs_resources[1].name)

        # make random 32byte binary file
        new_size = 32 
        with open(test_file, 'wb') as f:
            f.write(os.urandom(new_size))

        # overwrite existing replica 0 with new file
        options = {kw.FORCE_FLAG_KW: '', kw.DEST_RESC_NAME_KW: ufs_resources[0].name}
        session.data_objects.put(test_file, collection + '/', **options)

        # delete file
        os.remove(test_file)

        # ensure that sizes of the replicas are distinct
        obj = session.data_objects.get(obj_path, test_dir)
        self.assertEqual(obj.replicas[0].size, new_size)
        self.assertEqual(obj.replicas[1].size, original_size)

        # remove object
        obj.unlink(force=True)
        # delete file
        os.remove(test_file)

        # remove ufs resources
        for resource in ufs_resources:
            resource.remove()

    def test_obj_put_get(self):
        # Can't do one step open/create with older servers
        if self.sess.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        # test vars
        test_dir = '/tmp'
        filename = 'obj_put_get_test_file'
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path

        # make random 16M binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 1024 * 16))

        # compute file checksum
        digest = self.sha256_checksum(test_file)

        # put file in test collection
        self.sess.data_objects.put(test_file, collection + '/')

        # delete file
        os.remove(test_file)

        # get file back
        obj_path = '{collection}/{filename}'.format(**locals())
        self.sess.data_objects.get(obj_path, test_dir)

        # re-compute and verify checksum
        self.assertEqual(digest, self.sha256_checksum(test_file))

        # delete file
        os.remove(test_file)


    def test_obj_create_to_default_resource(self):
        if self.sess.server_version < (4, 0, 0):
            self.skipTest('For iRODS 4+')

        # make another UFS resource
        session = self.sess
        resource_name = 'ufs'
        resource_type = 'unixfilesystem'
        resource_host = session.host
        resource_path = '/tmp/' + resource_name
        session.resources.create(resource_name, resource_type, resource_host, resource_path)

        # set default resource to new UFS resource
        session.default_resource = resource_name

        # test object
        collection = self.coll_path
        filename = 'create_def_resc_test_file'
        obj_path = "{collection}/{filename}".format(**locals())
        content = ''.join(random.choice(string.printable) for _ in range(1024))

        # make object in test collection
        obj = helpers.make_object(session, obj_path, content=content)

        # get object and confirm resource
        self.assertEqual(obj.replicas[0].resource_name, resource_name)

        # delete obj and second resource
        obj.unlink(force=True)
        session.resources.remove(resource_name)


    def test_obj_put_to_default_resource(self):
        # Can't do one step open/create with older servers
        if self.sess.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        # make another UFS resource
        session = self.sess
        resource_name = 'ufs'
        resource_type = 'unixfilesystem'
        resource_host = session.host
        resource_path = '/tmp/' + resource_name
        session.resources.create(resource_name, resource_type, resource_host, resource_path)

        # set default resource to new UFS resource
        session.default_resource = resource_name

        # make a local file with random text content
        content = ''.join(random.choice(string.printable) for _ in range(1024))
        filename = 'testfile.txt'
        file_path = os.path.join('/tmp', filename)
        with open(file_path, 'w') as f:
            f.write(content)

        # put file
        collection = self.coll_path
        obj_path = '{collection}/{filename}'.format(**locals())

        session.data_objects.put(file_path, obj_path)

        # get object and confirm resource
        obj = session.data_objects.get(obj_path)
        self.assertEqual(obj.replicas[0].resource_name, resource_name)

        # cleanup
        os.remove(file_path)
        obj.unlink(force=True)
        session.resources.remove(resource_name)


    def test_obj_put_to_default_resource_from_env_file(self):
        # Can't do one step open/create with older servers
        if self.sess.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        # make another UFS resource
        session = self.sess
        resource_name = 'ufs'
        resource_type = 'unixfilesystem'
        resource_host = session.host
        resource_path = '/tmp/' + resource_name
        session.resources.create(resource_name, resource_type, resource_host, resource_path)

        # make a copy of the irods env file with 'ufs0' as the default resource
        env_file = os.path.expanduser('~/.irods/irods_environment.json')
        new_env_file = '/tmp/irods_environment.json'

        with open(env_file) as f, open(new_env_file, 'w') as new_f:
            irods_env = json.load(f)
            irods_env['irods_default_resource'] = resource_name
            json.dump(irods_env, new_f)

        # now open a new session with our modified environment file
        with helpers.make_session(irods_env_file=new_env_file) as new_session:

            # make a local file with random text content
            content = ''.join(random.choice(string.printable) for _ in range(1024))
            filename = 'testfile.txt'
            file_path = os.path.join('/tmp', filename)
            with open(file_path, 'w') as f:
                f.write(content)

            # put file
            collection = self.coll_path
            obj_path = '{collection}/{filename}'.format(**locals())

            new_session.data_objects.put(file_path, obj_path)

            # get object and confirm resource
            obj = new_session.data_objects.get(obj_path)
            self.assertEqual(obj.replicas[0].resource_name, resource_name)

            # remove object
            obj.unlink(force=True)

        # delete second resource
        session.resources.remove(resource_name)

        # cleanup
        os.remove(file_path)
        os.remove(new_env_file)


    def test_obj_put_and_return_data_object(self):
        # Can't do one step open/create with older servers
        if self.sess.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        # make another UFS resource
        session = self.sess
        resource_name = 'ufs'
        resource_type = 'unixfilesystem'
        resource_host = session.host
        resource_path = '/tmp/' + resource_name
        session.resources.create(resource_name, resource_type, resource_host, resource_path)

        # set default resource to new UFS resource
        session.default_resource = resource_name

        # make a local file with random text content
        content = ''.join(random.choice(string.printable) for _ in range(1024))
        filename = 'testfile.txt'
        file_path = os.path.join('/tmp', filename)
        with open(file_path, 'w') as f:
            f.write(content)

        # put file
        collection = self.coll_path
        obj_path = '{collection}/{filename}'.format(**locals())

        new_file = session.data_objects.put(file_path, obj_path, return_data_object=True)

        # get object and confirm resource
        obj = session.data_objects.get(obj_path)
        self.assertEqual(new_file.replicas[0].resource_name, obj.replicas[0].resource_name)

        # cleanup
        os.remove(file_path)
        obj.unlink(force=True)
        session.resources.remove(resource_name)



    def test_force_get(self):
        # Can't do one step open/create with older servers
        if self.sess.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        # test vars
        test_dir = '/tmp'
        filename = 'force_get_test_file'
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path

        # make random 4M binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 1024 * 4))

        # put file in test collection
        self.sess.data_objects.put(test_file, collection + '/')

        # try to get file back
        obj_path = '{collection}/{filename}'.format(**locals())
        with self.assertRaises(ex.OVERWRITE_WITHOUT_FORCE_FLAG):
            self.sess.data_objects.get(obj_path, test_dir)

        # this time with force flag
        options = {kw.FORCE_FLAG_KW: ''}
        self.sess.data_objects.get(obj_path, test_dir, **options)

        # delete file
        os.remove(test_file)


    def test_register(self):
        # skip if server is remote
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # test vars
        test_dir = '/tmp'
        filename = 'register_test_file'
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path
        obj_path = '{collection}/{filename}'.format(**locals())

        # make random 4K binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 4))

        # register file in test collection
        self.sess.data_objects.register(test_file, obj_path)

        # confirm object presence
        obj = self.sess.data_objects.get(obj_path)

        # in a real use case we would likely
        # want to leave the physical file on disk
        obj.unregister()

        # delete file
        os.remove(test_file)


    def test_register_with_checksum(self):
        # skip if server is remote
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # test vars
        test_dir = '/tmp'
        filename = 'register_test_file'
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path
        obj_path = '{collection}/{filename}'.format(**locals())

        # make random 4K binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 4))

        # register file in test collection
        options = {kw.VERIFY_CHKSUM_KW: ''}
        self.sess.data_objects.register(test_file, obj_path, **options)

        # confirm object presence and verify checksum
        obj = self.sess.data_objects.get(obj_path)

        # don't use obj.path (aka logical path)
        phys_path = obj.replicas[0].path
        digest = helpers.compute_sha256_digest(phys_path)
        self.assertEqual(obj.checksum, "sha2:{}".format(digest))

        # leave physical file on disk
        obj.unregister()

        # delete file
        os.remove(test_file)

    def test_modDataObjMeta(self):
        # skip if server is remote
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # test vars
        test_dir = '/tmp'
        filename = 'register_test_file'
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path
        obj_path = '{collection}/{filename}'.format(**locals())

        # make random 4K binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 4))

        # register file in test collection
        self.sess.data_objects.register(test_file, obj_path)

        qu = self.sess.query(Collection.id).filter(Collection.name == collection)
        for res in qu:
            collection_id = res[Collection.id]

        qu = self.sess.query(DataObject.size, DataObject.modify_time).filter(DataObject.name == filename, DataObject.collection_id == collection_id)
        for res in qu:
            self.assertEqual(int(res[DataObject.size]), 1024 * 4)
        self.sess.data_objects.modDataObjMeta({"objPath" : obj_path}, {"dataSize":1024, "dataModify":4096})

        qu = self.sess.query(DataObject.size, DataObject.modify_time).filter(DataObject.name == filename, DataObject.collection_id == collection_id)
        for res in qu:
            self.assertEqual(int(res[DataObject.size]), 1024)
            self.assertEqual(res[DataObject.modify_time], datetime.utcfromtimestamp(4096))

        # leave physical file on disk
        self.sess.data_objects.unregister(obj_path)

        # delete file
        os.remove(test_file)

    def test_register_with_xml_special_chars(self):
        # skip if server is remote
        if self.sess.host not in ('localhost', socket.gethostname()):
            self.skipTest('Requires access to server-side file(s)')

        # test vars
        test_dir = '/tmp'
        filename = '''aaa'"<&test&>"'_file'''
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path
        obj_path = '{collection}/{filename}'.format(**locals())

        # make random 4K binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 4))

        # register file in test collection
        self.sess.data_objects.register(test_file, obj_path)

        # confirm object presence
        obj = self.sess.data_objects.get(obj_path)

        # in a real use case we would likely
        # want to leave the physical file on disk
        obj.unregister()

        # delete file
        os.remove(test_file)

    def test_get_data_objects(self):
        # Can't do one step open/create with older servers
        if self.sess.server_version <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')

        # test vars
        test_dir = '/tmp'
        filename = 'get_data_objects_test_file'
        test_file = os.path.join(test_dir, filename)
        collection = self.coll.path

        # make random 16byte binary file
        original_size = 16
        with open(test_file, 'wb') as f:
            f.write(os.urandom(original_size))

        # make ufs resources
        ufs_resources = []
        for i in range(2):
            resource_name = 'ufs{}'.format(i)
            resource_type = 'unixfilesystem'
            resource_host = self.sess.host
            resource_path = '/tmp/{}'.format(resource_name)
            ufs_resources.append(self.sess.resources.create(
                resource_name, resource_type, resource_host, resource_path))

        # make passthru resource and add ufs1 as a child
        passthru_resource = self.sess.resources.create('pt', 'passthru')
        self.sess.resources.add_child(passthru_resource.name, ufs_resources[1].name)

        # put file in test collection and replicate
        obj_path = '{collection}/{filename}'.format(**locals())
        options = {kw.DEST_RESC_NAME_KW: ufs_resources[0].name}
        self.sess.data_objects.put(test_file, '{collection}/'.format(**locals()), **options)
        self.sess.data_objects.replicate(obj_path, passthru_resource.name)

        # ensure that replica info is populated
        obj = self.sess.data_objects.get(obj_path)
        for i in ["number","status","resource_name","path","resc_hier"]:
            self.assertIsNotNone(obj.replicas[0].__getattribute__(i))
            self.assertIsNotNone(obj.replicas[1].__getattribute__(i))

        # ensure replica info is sensible
        for i in range(2):
            self.assertEqual(obj.replicas[i].number, i)
            self.assertEqual(obj.replicas[i].status, '1')
            self.assertEqual(obj.replicas[i].path.split('/')[-1], filename)
            self.assertEqual(obj.replicas[i].resc_hier.split(';')[-1], ufs_resources[i].name)

        self.assertEqual(obj.replicas[0].resource_name, ufs_resources[0].name)
        if self.sess.server_version < (4, 2, 0):
            self.assertEqual(obj.replicas[i].resource_name, passthru_resource.name)
        else:
            self.assertEqual(obj.replicas[i].resource_name, ufs_resources[1].name)
        self.assertEqual(obj.replicas[1].resc_hier.split(';')[0], passthru_resource.name)

        # remove object
        obj.unlink(force=True)
        # delete file
        os.remove(test_file)

        # remove resources
        self.sess.resources.remove_child(passthru_resource.name, ufs_resources[1].name)
        passthru_resource.remove()
        for resource in ufs_resources:
            resource.remove()


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
