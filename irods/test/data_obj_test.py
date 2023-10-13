#! /usr/bin/env python
from __future__ import absolute_import
import base64
import concurrent.futures
import contextlib  # check if redundant
import hashlib
import io
import itertools
import json
import logging
import os
import random
import re
import socket
import stat
import string
import sys
import subprocess
import time
import unittest
import xml.etree.ElementTree

ip_pattern = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)$')
localhost_with_optional_domain_pattern = re.compile('localhost(\.\S\S*)?$')

def is_localhost_ip(s):
    match = ip_pattern.match(s)
    octets = [] if not match else [int(_) for _ in match.groups()]
    return [127,0,0,1] <= octets <= [127,255,255,254]

def is_localhost_synonym(name):
    return localhost_with_optional_domain_pattern.match(name.lower()) or \
           is_localhost_ip(name)

from irods.access import iRODSAccess
from irods.models import Collection, DataObject
from irods.test.helpers import iRODSUserLogins
import irods.exception as ex
from irods.column import Criterion
from irods.data_object import chunks, irods_dirname
import irods.test.helpers as helpers
import irods.test.modules as test_modules
import irods.keywords as kw
import irods.client_configuration as config
from irods.manager import data_object_manager
from irods.message import RErrorStack
from irods.message import ( ET, XML_Parser_Type, default_XML_parser, current_XML_parser )
from datetime import datetime
from tempfile import NamedTemporaryFile, gettempdir
from irods.test.helpers import (unique_name, my_function_name)
from irods.ticket import Ticket
import irods.parallel
from irods.manager.data_object_manager import Server_Checksum_Warning

RODSUSER = 'nonadmin'

MEBI = 1024**2

def make_ufs_resc_in_tmpdir(session, base_name, allow_local = False, client_vault_mode = (True,)):
    # Parameters
    # ----------
    # base_name         -  The name for the resource, as well as the root directory of the Vault.  Use something random and unlikely to collide.
    # allow_local       -  Whether to allow the resource's vault to be located under a non-shared ie. "/tmp" style directory.
    # client_vault_mode -  A tuple of (client_mkdir[, mode_OR_mask]):
    #                          client_mkdir - whether to call mkdir on the vault-path from the client side, and ...
    #                          mode_OR_mask - if so, what mode bits to be OR'ed into the permission of the vault path after creation
    #                                         (A typical value might be : 0o777 | stat.S_ISGID, to guarantee iRODS has permissions on the vault)
    tmpdir = helpers.irods_shared_tmp_dir()
    if not tmpdir and allow_local:
        tmpdir = os.getenv('TMPDIR') or '/tmp'
    if not tmpdir:
        raise RuntimeError("Must have filesystem path shareable with server.")

    full_phys_dir = os.path.join(tmpdir,base_name)

    if client_vault_mode[0]:
        if not os.path.exists(full_phys_dir):
            os.mkdir(full_phys_dir)
        guarantee_mode_bits = tuple(client_vault_mode[1:])
        if guarantee_mode_bits != ():
            mode = os.stat(full_phys_dir).st_mode
            os.chmod(full_phys_dir, mode | guarantee_mode_bits[0])

    session.resources.create(base_name,'unixfilesystem',session.host,full_phys_dir)
    return full_phys_dir


class TestDataObjOps(unittest.TestCase):


    from irods.test.helpers import (create_simple_resc)

    def setUp(self):
        # Create test collection
        self.sess = helpers.make_session()
        self.coll_path = '/{}/home/{}/test_dir'.format(self.sess.zone, self.sess.username)
        self.coll = helpers.make_collection(self.sess, self.coll_path)
        with self.sess.pool.get_connection() as conn:
            self.SERVER_VERSION = conn.server_version

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    @staticmethod
    def In_Memory_Stream():
        return io.BytesIO() if sys.version_info < (3,) else io.StringIO()


    @contextlib.contextmanager
    def create_resc_hierarchy (self, Root, Leaf = None):
        if not Leaf:
            Leaf = 'simple_leaf_resc_' + unique_name (my_function_name(), datetime.now())
            y_value = (Root,Leaf)
        else:
            y_value = ';'.join([Root,Leaf])
        self.sess.resources.create(Leaf,'unixfilesystem',
                               host = self.sess.host,
                               path='/tmp/' + Leaf)
        self.sess.resources.create(Root,'passthru')
        self.sess.resources.add_child(Root,Leaf)
        try:
            yield  y_value
        finally:
            self.sess.resources.remove_child(Root,Leaf)
            self.sess.resources.remove(Leaf)
            self.sess.resources.remove(Root)

    def test_data_write_stales_other_repls__ref_irods_5548(self):
        test_data = 'irods_5548_testfile'
        test_coll = '/{0.zone}/home/{0.username}'.format(self.sess)
        test_path = test_coll + "/" + test_data
        demoResc = self.sess.resources.get('demoResc').name
        self.sess.data_objects.open(test_path, 'w',**{kw.DEST_RESC_NAME_KW: demoResc}).write(b'random dater')

        with self.create_simple_resc() as newResc:
            try:
                with self.sess.data_objects.open(test_path, 'a', **{kw.DEST_RESC_NAME_KW: newResc}) as d:
                    d.seek(0,2)
                    d.write(b'z')
                data = self.sess.data_objects.get(test_path)
                statuses = { repl.resource_name: repl.status for repl in data.replicas }
                self.assertEqual( '0', statuses[demoResc] )
                self.assertEqual( '1', statuses[newResc] )
            finally:
                self.cleanup_data_object(test_path)


    def cleanup_data_object(self,data_logical_path):
        try:
            self.sess.data_objects.get(data_logical_path).unlink(force = True)
        except ex.DataObjectDoesNotExist:
            pass


    def write_and_check_replica_on_parallel_connections( self, data_object_path, root_resc, caller_func, required_num_replicas = 1, seconds_to_wait_for_replicas = 10):
        """Helper function for testing irods/irods#5548 and irods/irods#5848.

        Writes the  string "books\n" to a replica, but not as a single write operation.
        It is done piecewise on two independent connections, essentially simulating parallel "put".
        Then we assert the file contents and dispose of the data object."""

        try:
            self.sess.data_objects.create(data_object_path, resource = root_resc)
            for _ in range( seconds_to_wait_for_replicas ):
                if required_num_replicas <= len( self.sess.data_objects.get(data_object_path).replicas ): break
                time.sleep(1)
            else:
                raise RuntimeError("Did not see %d replicas" % required_num_replicas)
            fd1 = self.sess.data_objects.open(data_object_path, 'w', **{kw.DEST_RESC_NAME_KW: root_resc} )
            (replica_token, hier_str) = fd1.raw.replica_access_info()
            fd2 = self.sess.data_objects.open(data_object_path, 'a', finalize_on_close = False, **{kw.RESC_HIER_STR_KW: hier_str,
                                                                                                   kw.REPLICA_TOKEN_KW: replica_token})
            fd2.seek(4) ; fd2.write(b's\n')
            fd1.write(b'book')
            fd2.close()
            fd1.close()
            with self.sess.data_objects.open(data_object_path, 'r', **{kw.DEST_RESC_NAME_KW: root_resc} ) as f:
                self.assertEqual(f.read(), b'books\n')
        except Exception as e:
            logging.debug('Exception %r in [%s], called from [%s]', e, my_function_name(), caller_func)
            raise
        finally:
            if 'fd2' in locals() and not fd2.closed: fd2.close()
            if 'fd1' in locals() and not fd1.closed: fd1.close()
            self.cleanup_data_object( data_object_path )


    def test_parallel_conns_to_repl_with_cousin__irods_5848(self):
        """Cousins = resource nodes not sharing any common parent nodes."""
        data_path = '/{0.zone}/home/{0.username}/cousin_resc_5848.dat'.format(self.sess)

        #
        # -- Create replicas of a data object under two different root resources and test parallel write: --

        with self.create_simple_resc() as newResc:

            # - create empty data object on demoResc
            self.sess.data_objects.open(data_path, 'w',**{kw.DEST_RESC_NAME_KW: 'demoResc'})

            # - replicate data object to newResc
            self.sess.data_objects.get(data_path).replicate(newResc)

            # - test whether a write to the replica on newResc functions correctly.
            self.write_and_check_replica_on_parallel_connections( data_path, newResc, my_function_name(), required_num_replicas = 2)


    def test_parallel_conns_with_replResc__irods_5848(self):
        session = self.sess
        replication_resource = None
        ufs_resources = []
        replication_resource = self.sess.resources.create('repl_resc_1_5848', 'replication')
        number_of_replicas = 2
        # -- Create replicas of a data object by opening it on a replication resource; then, test parallel write --
        try:
            # Build up the replication resource with `number_of_replicas' being the # of children
            for i in range(number_of_replicas):
                resource_name = unique_name(my_function_name(),i)
                resource_type = 'unixfilesystem'
                resource_host = session.host
                resource_path = '/tmp/' + resource_name
                ufs_resources.append(session.resources.create(
                    resource_name, resource_type, resource_host, resource_path))
                session.resources.add_child(replication_resource.name, resource_name)
            data_path = '/{0.zone}/home/{0.username}/Replicated_5848.dat'.format(self.sess)

            # -- Perform the check of writing by a single replica (which is unspecified, but one of the `number_of_replicas`
            #    will be selected by voting)

            self.write_and_check_replica_on_parallel_connections (data_path, replication_resource.name, my_function_name(), required_num_replicas = 2)
        finally:
            for resource in ufs_resources:
                session.resources.remove_child(replication_resource.name, resource.name)
                resource.remove()
            if replication_resource:
                replication_resource.remove()

    def test_put_get_parallel_autoswitch_A__235(self):
        if not self.sess.data_objects.should_parallelize_transfer(server_version_hint = self.SERVER_VERSION):
            self.skipTest('Skip unless detected server version is 4.2.9')
        if getattr(data_object_manager,'DEFAULT_NUMBER_OF_THREADS',None) in (1, None):
            self.skipTest('Data object manager not configured for parallel puts and gets')
        Root  = 'pt235'
        Leaf  = 'resc235'
        files_to_delete = []
        # This test does the following:
        #  - set up a small resource hierarchy and generate a file large enough to trigger parallel transfer
        #  - `put' the file to iRODS, then `get' it back, comparing the resulting two disk files and making
        #    sure that the parallel routines were invoked to do both transfers

        with self.create_resc_hierarchy(Root) as (Root_ , Leaf):
            self.assertEqual(Root , Root_)
            self.assertIsInstance( Leaf, str)
            datafile = NamedTemporaryFile (prefix='getfromhier_235_',delete=True)
            datafile.write( os.urandom( data_object_manager.MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE + 1 ))
            datafile.flush()
            base_name = os.path.basename(datafile.name)
            data_obj_name = '/{0.zone}/home/{0.username}/{1}'.format(self.sess, base_name)
            options = { kw.DEST_RESC_NAME_KW:Root,
                        kw.RESC_NAME_KW:Root }

            PUT_LOG = self.In_Memory_Stream()
            GET_LOG = self.In_Memory_Stream()
            NumThreadsRegex = re.compile('^num_threads\s*=\s*(\d+)',re.MULTILINE)

            try:
                logger = logging.getLogger('irods.parallel')
                with helpers.enableLogging(logger, logging.StreamHandler, (PUT_LOG,), level_ = logging.DEBUG):
                    self.sess.data_objects.put(datafile.name, data_obj_name, num_threads = 0, **options)  # - PUT
                    match = NumThreadsRegex.search (PUT_LOG.getvalue())
                    self.assertTrue (match is not None and int(match.group(1)) >= 1) # - PARALLEL code path taken?

                with helpers.enableLogging(logger, logging.StreamHandler, (GET_LOG,), level_ = logging.DEBUG):
                    self.sess.data_objects.get(data_obj_name, datafile.name+".get", num_threads = 0, **options) # - GET
                    match = NumThreadsRegex.search (GET_LOG.getvalue())
                    self.assertTrue (match is not None and int(match.group(1)) >= 1) # - PARALLEL code path taken?

                files_to_delete += [datafile.name + ".get"]

                with open(datafile.name, "rb") as f1, open(datafile.name + ".get", "rb") as f2:
                    self.assertEqual ( f1.read(), f2.read() )

                q = self.sess.query (DataObject.name,DataObject.resc_hier).filter( DataObject.name == base_name,
                                                                                   DataObject.resource_name == Leaf)
                replicas = list(q)
                self.assertEqual( len(replicas), 1 )
                self.assertEqual( replicas[0][DataObject.resc_hier] , ';'.join([Root,Leaf]) )

            finally:
                self.sess.data_objects.unlink( data_obj_name, force = True)
                for n in files_to_delete: os.unlink(n)

    def test_open_existing_dataobj_in_resource_hierarchy__232(self):
        Root  = 'pt1'
        Leaf  = 'resc1'
        with self.create_resc_hierarchy(Root,Leaf) as hier_str:
            obj = None
            try:
                datafile = NamedTemporaryFile (prefix='getfromhier_232_',delete=True)
                datafile.write(b'abc\n')
                datafile.flush()
                fname = datafile.name
                bname = os.path.basename(fname)
                LOGICAL = self.coll_path + '/' + bname
                self.sess.data_objects.put(fname,LOGICAL, **{kw.DEST_RESC_NAME_KW:Root})
                self.assertEqual([bname], [res[DataObject.name] for res in
                                           self.sess.query(DataObject.name).filter(DataObject.resc_hier == hier_str)])
                obj = self.sess.data_objects.get(LOGICAL)
                obj.open('a') # prior to #232 fix, raises DIRECT_CHILD_ACCESS
            finally:
                if obj: obj.unlink(force=True)

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

    def test_routine_verify_chksum_operation( self ):

        if self.sess.server_version < (4, 2, 11):
            self.skipTest('iRODS servers < 4.2.11 do not raise a checksum warning')

        dobj_path =  '/{0.zone}/home/{0.username}/verify_chksum.dat'.format(self.sess)
        self.sess.data_objects.create(dobj_path)
        try:
            with self.sess.data_objects.open(dobj_path,'w') as f:
                f.write(b'abcd')
            checksum = self.sess.data_objects.chksum(dobj_path)
            self.assertGreater(len(checksum),0)
            r_err_stk = RErrorStack()
            warning = None
            try:
                self.sess.data_objects.chksum(dobj_path, **{'r_error': r_err_stk, kw.VERIFY_CHKSUM_KW:''})
            except Server_Checksum_Warning as exc_:
                warning = exc_
            # There's one replica and it has a checksum, so expect no errors or hints from error stack.
            self.assertIsNone(warning)
            self.assertEqual(0, len(r_err_stk))
        finally:
            self.sess.data_objects.unlink(dobj_path, force = True)

    def test_verify_chksum__282_287( self ):

        if self.sess.server_version < (4, 2, 11):
            self.skipTest('iRODS servers < 4.2.11 do not raise a checksum warning')

        with self.create_simple_resc() as R, self.create_simple_resc() as R2, NamedTemporaryFile(mode = 'wb') as f:
            f.write(b'abcxyz\n')
            f.flush()
            coll_path = '/{0.zone}/home/{0.username}' .format(self.sess)
            dobj_path = coll_path + '/' + os.path.basename(f.name)
            Data = self.sess.data_objects
            r_err_stk = RErrorStack()
            try:
                demoR = self.sess.resources.get('demoResc').name  # Assert presence of demoResc and
                Data.put( f.name, dobj_path )                     # Establish three replicas of data object.
                Data.replicate( dobj_path, resource = R)
                Data.replicate( dobj_path, resource = R2)
                my_object = Data.get(dobj_path)

                my_object.chksum( **{kw.RESC_NAME_KW:demoR} )  # Make sure demoResc has the only checksummed replica of the three.
                my_object = Data.get(dobj_path)                # Refresh replica list to get checksum(s).

                Baseline_repls_without_checksum = set( r.number for r in my_object.replicas if not r.checksum )

                warn_exception = None
                try:
                    my_object.chksum( r_error = r_err_stk, **{kw.VERIFY_CHKSUM_KW:''} )   # Verify checksums without auto-vivify.
                except Server_Checksum_Warning as warn:
                    warn_exception = warn

                self.assertIsNotNone(warn_exception, msg = "Expected exception of type [Server_Checksum_Warning] was not received.")

                # -- Make sure integer codes are properly reflected for checksum warnings.
                self.assertEqual (2, len([e for e in r_err_stk if e.status_ == ex.rounded_code('CAT_NO_CHECKSUM_FOR_REPLICA')]))

                NO_CHECKSUM_MESSAGE_PATTERN = re.compile( 'No\s+Checksum\s+Available.+\s+Replica\s\[(\d+)\]', re.IGNORECASE)

                Reported_repls_without_checksum = set( int(match.group(1)) for match in [ NO_CHECKSUM_MESSAGE_PATTERN.search(e.raw_msg_)
                                                                                          for e in r_err_stk ]
                                                       if match is not None )

                # Ensure that VERIFY_CHKSUM_KW reported all replicas lacking a checksum
                self.assertEqual (Reported_repls_without_checksum,
                                  Baseline_repls_without_checksum)
            finally:
                if Data.exists (dobj_path):
                    Data.unlink (dobj_path, force = True)


    def test_compute_chksum( self ):

        with self.create_simple_resc() as R, NamedTemporaryFile(mode = 'wb') as f:
            coll_path = '/{0.zone}/home/{0.username}' .format(self.sess)
            dobj_path = coll_path + '/' + os.path.basename(f.name)
            Data = self.sess.data_objects
            try:
                f.write(b'some content bytes ...\n')
                f.flush()
                Data.put( f.name, dobj_path )

                # get original checksum and resource name
                my_object = Data.get(dobj_path)
                orig_resc = my_object.replicas[0].resource_name
                chk1 = my_object.chksum()

                # repl to new resource and iput to that new replica
                Data.replicate( dobj_path, resource = R)
                f.write(b'...added bytes\n')
                f.flush()
                Data.put( f.name, dobj_path, **{kw.DEST_RESC_NAME_KW: R,
                                                kw.FORCE_FLAG_KW: '1'})
                # compare checksums
                my_object = Data.get(dobj_path)
                chk2 = my_object.chksum( **{kw.RESC_NAME_KW : R} )
                chk1b = my_object.chksum( **{kw.RESC_NAME_KW : orig_resc} )
                self.assertEqual (chk1, chk1b)
                self.assertNotEqual (chk1, chk2)

            finally:
                if Data.exists (dobj_path): Data.unlink (dobj_path, force = True)


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


    def test_create_from_invalid_path__250(self):
        possible_exceptions = { ex.SYS_INVALID_INPUT_PARAM: (lambda serv_vsn : serv_vsn <= (4,2,8)),
                                ex.CAT_UNKNOWN_COLLECTION:  (lambda serv_vsn : (4,2,9) <= serv_vsn < (4,3,0)),
                                ex.SYS_INVALID_FILE_PATH:   (lambda serv_vsn : (4,3,0) <= serv_vsn)
                              }
        raisedExc = None
        try:
            self.sess.data_objects.create('t')
        except Exception as exc:
            raisedExc = exc
        server_version_cond = possible_exceptions.get(type(raisedExc))
        self.assertTrue(server_version_cond is not None)
        self.assertTrue(server_version_cond(self.sess.server_version))


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
        self.sess.data_objects.unlink(new_path, force = True)


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

    #
    # To run these tests, we require a local iRODS connection but not one with a localhost-equivalent hostname.
    #
    def _skip_unless_connected_to_local_computer_by_other_than_localhost_synonym(self):
        if self.sess.host != socket.gethostname() or is_localhost_synonym(self.sess.host):
            self.skipTest('This test requires being connected to a local server, but not via "localhost" or a synonym.')

    class WrongUserType(RuntimeError): pass

    @classmethod
    def setUpClass(cls):
        adm = helpers.make_session()
        if adm.users.get(adm.username).type != 'rodsadmin':
            error = cls.WrongUserType('Must be an iRODS admin to run tests in class {0.__name__}'.format(cls))
            raise error
        cls.logins = iRODSUserLogins(adm)
        cls.logins.create_user(RODSUSER,'abc123')

    @classmethod
    def tearDownClass(cls):
        # TODO: Skipping this will result in an interpreter seg fault for Py3.6 but not 3.11; why?
        del cls.logins

    def _data_object_and_associated_ticket(self, 
                                           data_name='',             # A random name will be generated by default.
                                           content=None,             # Content to use if creating data object internally.
                                           auto_delete_data = True,  # Whether to delete up the data object in finalization.
                                           ticket_access=''          # No ticket is generated unless string is nonzero length.
                                           ):
        ticket = [None]
        data = [None]
        if '/' in data_name:
            data_path = data_name
        else:
            if not data_name:
                data_name = helpers.unique_name(helpers.my_function_name(), datetime.now())
            data_path = helpers.home_collection(self.sess) + "/" + data_name
        def create_data(open_options):
            if content is not None and not self.sess.data_objects.exists(data_path):
                with self.sess.data_objects.open(data_path, "w", **dict(open_options)) as f:
                    f.write(content)
            data[0] = data_path
        try:
            if ticket_access:
                user_session = self.logins.session_for_user(RODSUSER)
                def initialize(open_options=()):
                    create_data(open_options)
                    # Activate ticket for test session:
                    ticket_logical_path = data_path if self.sess.data_objects.exists(data_path) else irods_dirname(data_path)
                    ticket[0] = Ticket(self.sess).issue(ticket_access, ticket_logical_path)
                    Ticket(user_session, ticket[0].string).supply()
            else:
                user_session = self.sess
                initialize = lambda open_options=(): \
                                 create_data(open_options)
            # Can be called early to clear resources of data objects before their deletion
            def finalize():
                if auto_delete_data and data[0]:
                    self.sess.data_objects.unlink(data[0], force=True)
                    data[0]=None
            yield { 'path':data_path, 'session':user_session, 'finalize': finalize, 'initialize':initialize, 'ticket_access': ticket_access }
        finally:
            if ticket[0]:
                ticket[0].delete()
            finalize()

    data_object_and_associated_ticket = contextlib.contextmanager(_data_object_and_associated_ticket)

    def test_redirect_in_data_object_put_and_get_with_tickets__issue_452(self):
        for _,size in {'large':40*MEBI,
                       'small': 1*MEBI }.items():
            content = b'1024123'*(size//7)
            with self.data_object_and_associated_ticket(ticket_access='write') as data_ctx:
                self.do_test_redirect_in_data_object_put_and_get__issue_452(content,data_ctx)
            
    def test_redirect_in_data_object_put_and_get_without_tickets__issue_452(self):
        for _,size in {'large':40*MEBI,
                       'small': 1*MEBI  }.items():
            content = b'1024123'*(size//7)
            with self.data_object_and_associated_ticket(ticket_access='') as data_ctx:
                self.do_test_redirect_in_data_object_put_and_get__issue_452(content,data_ctx)

    def do_test_redirect_in_data_object_put_and_get__issue_452(self, content, data_ctx):
        self._skip_unless_connected_to_local_computer_by_other_than_localhost_synonym()
        if self.sess.server_version < (4, 3, 1):
            self.skipTest('Expects iRODS server version 4.3.1')
        LOCAL_FILE = mktemp()
        filename = ''
        try:
            with self.create_simple_resc(hostname = 'localhost') as rescName:
                with NamedTemporaryFile(delete = False) as f:
                    filename = f.name
                    f.write(content)
                data_ctx['initialize']()
                sess = data_ctx['session']
                remote_name = data_ctx['path']
                PUT_LOG = self.In_Memory_Stream()
                with helpers.enableLogging(logging.getLogger('irods.manager.data_object_manager'),
                                           logging.StreamHandler, (PUT_LOG,), level_ = logging.DEBUG),\
                     helpers.enableLogging(logging.getLogger('irods.parallel'),
                                           logging.StreamHandler, (PUT_LOG,), level_ = logging.DEBUG):
                    sess.data_objects.put(filename, remote_name, **{kw.DEST_RESC_NAME_KW: rescName})
                def srch(BUF):
                    nthr = 0
                    search_text = BUF.getvalue()
                    find_iterator = itertools.chain( re.finditer('redirect_to_host = (\S+)', search_text),
                                                     re.finditer('target_host = (\S+)', search_text) )
                    for match in find_iterator:
                        nthr += 1
                        self.assertEqual(match.group(1), 'localhost')
                    occur_threshold = (1 if len(content) <= 32*MEBI else 2)
                    self.assertGreaterEqual(nthr, occur_threshold)
                srch(PUT_LOG)
                generator = None
                # Activate a read ticket on a new session if necessary, and attempt a GET
                if data_ctx['ticket_access']:
                    for access in iRODSAccess('own',remote_name,self.sess.username), \
                                  iRODSAccess('null',remote_name,sess.username):
                        self.sess.acls.set(access, admin = True)
                    generator = self._data_object_and_associated_ticket(data_name=remote_name, auto_delete_data = False, ticket_access='read')
                    # Emulate the 'with'-block construction for the read ticket:
                    data_ctx_get = next(generator)
                    data_ctx_get['initialize']()
                    sess = data_ctx_get['session']
                GET_LOG = self.In_Memory_Stream()
                with helpers.enableLogging(logging.getLogger('irods.manager.data_object_manager'),
                                           logging.StreamHandler, (GET_LOG,), level_ = logging.DEBUG),\
                     helpers.enableLogging(logging.getLogger('irods.parallel'),
                                           logging.StreamHandler, (GET_LOG,), level_ = logging.DEBUG):
                    sess.data_objects.get(remote_name,LOCAL_FILE)
                srch(GET_LOG)
                with open(LOCAL_FILE,'rb') as get_result:
                    self.assertTrue(content, get_result.read())
                # Finalize the emulated 'with'-block construction for the read ticket, if active:
                del generator
                data_ctx['finalize']()
        finally:
            if os.path.isfile(LOCAL_FILE):
                os.unlink(LOCAL_FILE)
            if filename:
                os.unlink(filename)

    def test_redirect_in_data_object_open__issue_452(self):
        self._skip_unless_connected_to_local_computer_by_other_than_localhost_synonym()
        if self.sess.server_version < (4, 3, 1):
            self.skipTest('Expects iRODS server version 4.3.1')
        sess = self.sess
        home = helpers.home_collection(sess)

        with self.create_simple_resc(hostname = 'localhost') as rescName:
            try:
                test_path = home + '/data_open_452'
                desc = sess.data_objects.open(test_path, 'w', **{kw.RESC_NAME_KW: rescName})
                self.assertEqual('localhost', desc.raw.session.host)
                desc.close()
                desc = sess.data_objects.open(test_path, 'r')
                self.assertEqual('localhost', desc.raw.session.host)
                desc.close()
            finally:
                if sess.data_objects.exists(test_path):
                    sess.data_objects.unlink(test_path, force=True)


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
            resource_name = unique_name(my_function_name(),i)
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
        # note (see irods/irods#4861): COPIES_KW might disappear in the future
        options = {kw.COPIES_KW: 1}
        for i in [1, 3, 5]:
            options[kw.REPL_NUM_KW] = str(i)
            obj.trim(**options)

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
        server_vsn = self.sess.server_version
        if server_vsn <= (4, 1, 4):
            self.skipTest('For iRODS 4.1.5 and newer')
        try:
            number_of_replicas = 7
            session = self.sess
            zone = session.zone
            username = session.username
            test_dir = '/tmp'
            filename = 'repave_replica_test_file.txt'
            test_file = os.path.join(test_dir, filename)
            obj_path = '/{zone}/home/{username}/{filename}'.format(**locals())
            ufs_resources = []

            # make test file
            obj_content = u'foobar'
            checksum = base64.b64encode(hashlib.sha256(obj_content.encode('utf-8')).digest()).decode()
            with open(test_file, 'w') as f:
                f.write(obj_content)

            # put test file onto default resource
            options = {kw.REG_CHKSUM_KW: ''}
            session.data_objects.put(test_file, obj_path, **options)

            # make ufs resources and replicate object
            for i in range(number_of_replicas):
                resource_name = unique_name(my_function_name(),i)
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

            options = {kw.REG_CHKSUM_KW: '', kw.ALL_KW: ''}
            session.data_objects.put(test_file, obj_path, **options)
            obj = session.data_objects.get(obj_path)

            # verify each replica's checksum
            for replica in obj.replicas:
                self.assertEqual(replica.checksum, 'sha2:{}'.format(checksum))

        finally:
            # remove data object
            data = self.sess.data_objects
            if data.exists(obj_path):
                data.unlink(obj_path,force=True)
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
            resource_name = unique_name(my_function_name(),i)
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


    def test_modDataObjMeta(self):
        test_dir = helpers.irods_shared_tmp_dir()
        # skip if server is remote
        loc_server = self.sess.host in ('localhost', socket.gethostname())
        if not(test_dir) and not (loc_server):
            self.skipTest('Requires access to server-side file(s)')

        # test vars
        resc_name = 'testDataObjMetaResc'
        filename = 'register_test_file'
        collection = self.coll.path
        obj_path = '{collection}/{filename}'.format(**locals())
        test_path = make_ufs_resc_in_tmpdir(self.sess, resc_name, allow_local = loc_server)
        test_file = os.path.join(test_path, filename)

        # make random 4K binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 4))

        # register file in test collection
        self.sess.data_objects.register(test_file, obj_path, **{kw.RESC_NAME_KW:resc_name})

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
            resource_name = unique_name(my_function_name(),i)
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


    def test_register(self):
        test_dir = helpers.irods_shared_tmp_dir()
        loc_server = self.sess.host in ('localhost', socket.gethostname())
        if not(test_dir) and not(loc_server):
            self.skipTest('data_obj register requires server has access to local or shared files')

        # test vars
        resc_name = "testRegisterOpResc"
        filename = 'register_test_file'
        collection = self.coll.path
        obj_path = '{collection}/{filename}'.format(**locals())

        test_path = make_ufs_resc_in_tmpdir(self.sess,resc_name, allow_local = loc_server)
        test_file = os.path.join(test_path, filename)

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
        test_dir = helpers.irods_shared_tmp_dir()
        loc_server = self.sess.host in ('localhost', socket.gethostname())
        if not(test_dir) and not(loc_server):
            self.skipTest('data_obj register requires server has access to local or shared files')

        # test vars
        resc_name= 'regWithChksumResc'
        filename = 'register_test_file'
        collection = self.coll.path
        obj_path = '{collection}/{filename}'.format(**locals())

        test_path = make_ufs_resc_in_tmpdir(self.sess, resc_name, allow_local = loc_server)
        test_file = os.path.join(test_path, filename)

        # make random 4K binary file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1024 * 4))

        # register file in test collection
        options = {kw.VERIFY_CHKSUM_KW: '', kw.RESC_NAME_KW: resc_name}
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


    def test_object_names_with_nonprintable_chars (self):
        if  (4,2,8) < self.sess.server_version < (4,2,11):
            self.skipTest('4.2.9 and 4.2.10 are known to fail as apostrophes in object names are problematic')
        test_dir = helpers.irods_shared_tmp_dir()
        loc_server = self.sess.host in ('localhost', socket.gethostname())
        if not(test_dir) and not(loc_server):
            self.skipTest('data_obj register requires server has access to local or shared files')
        temp_names = []
        vault = ''
        try:
            resc_name = 'regWithNonPrintableNamesResc'
            vault = make_ufs_resc_in_tmpdir(self.sess, resc_name, allow_local = loc_server)
            def enter_file_into_irods( session, filename, **kw_opt ):
                ET( XML_Parser_Type.QUASI_XML, session.server_version)
                basename = os.path.basename(filename)
                logical_path = '/{0.zone}/home/{0.username}/{basename}'.format(session,**locals())
                bound_method = getattr(session.data_objects, kw_opt['method'])
                bound_method( os.path.abspath(filename), logical_path, **kw_opt['options'] )
                d = session.data_objects.get(logical_path)
                Path_Good = (d.path == logical_path)
                session.data_objects.unlink( logical_path, force = True )
                session.cleanup()
                return Path_Good
            futr = []
            threadpool = concurrent.futures.ThreadPoolExecutor()
            fname = re.sub( r'[/]', '',
                            ''.join(map(chr,range(1,128))) )
            for opts in [
                    {'method':'put',     'options':{}},
                    {'method':'register','options':{kw.RESC_NAME_KW: resc_name}, 'dir':(test_dir or None)}
                ]:
                with NamedTemporaryFile(prefix=opts["method"]+"_"+fname, dir=opts.get("dir"), delete=False) as f:
                    f.write(b'hello')
                    temp_names += [f.name]
                ses = helpers.make_session()
                futr.append( threadpool.submit( enter_file_into_irods, ses, f.name, **opts ))
            results = [ f.result() for f in futr ]
            self.assertEqual (results, [True, True])
        finally:
            for name in temp_names:
                if os.path.exists(name):
                    os.unlink(name)
            if vault:
                self.sess.resources.remove( resc_name )
        self.assertIs( default_XML_parser(), current_XML_parser() )


    def test_data_open_on_leaf_is_disallowed__243(self):
        from irods.exception import DIRECT_CHILD_ACCESS
        root = unique_name(my_function_name(),datetime.now(),'root')
        home = helpers.home_collection(self.sess)
        with self.create_resc_hierarchy(root) as (_ , Leaf):
            with self.assertRaises(DIRECT_CHILD_ACCESS):
                self.sess.data_objects.open('{home}/disallowed_243'.format(**locals()), 'w', **{kw.RESC_NAME_KW:Leaf})

    def test_data_open_on_named_resource__243(self):
        s = self.sess
        data = s.data_objects
        home = helpers.home_collection(s)
        data_name = unique_name(my_function_name(),datetime.now(),'data')
        resc_name = unique_name(my_function_name(),datetime.now(),'resc')
        with self.create_simple_resc(resc_name) as resc:
            data_path = '{home}/{data_name}'.format(**locals())
            try:
                with data.open(data_path,'w',**{kw.RESC_NAME_KW:resc}) as f:
                    f.write(b'abc')
                d = data.get(data_path)
                self.assertEqual(len(d.replicas),1)
                self.assertEqual(d.replicas[0].resource_name, resc)
            finally:
                if data.exists(data_path):
                    data.unlink(data_path, force = True)


    class _temporary_resource_adopter:
        """When used as part of a context block, temporarily adopts the named
           child resources under the named parent resource.
        """
        def __init__(self, sess, parent, child_list=()):
            self.parent = parent
            self.child_list = child_list
            self.sess = sess
        def __enter__(self):
            for child in self.child_list:
                self.sess.resources.add_child(self.parent, child)
        def __exit__(self, *_):
            p_obj = self.sess.resources.get(self.parent)
            for child in set(self.child_list) & set(r.name for r in p_obj.children):
                self.sess.resources.remove_child(self.parent, child)


    def test_access_through_resc_hierarchy__243(self):
        s = self.sess
        data_path = '{coll}/{data}'.format(coll = helpers.home_collection(s),
                                           data = unique_name(my_function_name(),datetime.now()))
        try:
            s.resources.create('parent','deferred')
            with self.create_simple_resc('resc0_243') as r0, \
                 self.create_simple_resc('resc1_243') as r1, \
                 self._temporary_resource_adopter(s, parent = 'parent', child_list = (r0, r1)):

                hiers = ['parent;{0}'.format(r) for r in (r0,r1)]

                # Write two different replicas. Although the writing of the second will cause the first to become
                # stale, each replica can be independently read by specifying the resource hierarchy.
                for hier in hiers:
                    opts = {kw.RESC_HIER_STR_KW: hier}
                    with s.data_objects.open(data_path, 'a', **opts) as obj_io:
                        obj_io.seek(0)
                        obj_io.write(hier.encode('utf-8'))   # Write different content to each replica

                # Assert that we are able to read both replicas' content faithfully using the hierarchy string.
                for hier in hiers:
                    opts = {kw.RESC_HIER_STR_KW: hier}
                    with s.data_objects.open(data_path, 'r', **opts) as obj_io:
                        self.assertEqual(obj_io.read(),hier.encode('utf-8'))   # Does unique replica have unique content?

                s.data_objects.unlink(data_path, force = True)
        finally:
            s.resources.remove('parent')

    def test_register_with_xml_special_chars(self):
        test_dir = helpers.irods_shared_tmp_dir()
        loc_server = self.sess.host in ('localhost', socket.gethostname())
        if not(test_dir) and not(loc_server):
            self.skipTest('data_obj register requires server has access to local or shared files')

        # test vars
        resc_name = 'regWithXmlSpecialCharsResc'
        collection = self.coll.path
        filename = '''aaa'"<&test&>"'_file'''
        test_path = make_ufs_resc_in_tmpdir(self.sess, resc_name, allow_local = loc_server)
        try:
            test_file = os.path.join(test_path, filename)
            obj_path = '{collection}/{filename}'.format(**locals())

            # make random 4K binary file
            with open(test_file, 'wb') as f:
                f.write(os.urandom(1024 * 4))

            # register file in test collection
            self.sess.data_objects.register(test_file, obj_path, **{kw.RESC_NAME_KW: resc_name})

            # confirm object presence
            obj = self.sess.data_objects.get(obj_path)

        finally:
            # in a real use case we would likely
            # want to leave the physical file on disk
            obj.unregister()
            # delete file
            os.remove(test_file)
            # delete resource
            self.sess.resources.get(resc_name).remove()


    def test_unregister_can_target_replica__issue_435(self):
        test_dir = helpers.irods_shared_tmp_dir()
        loc_server = self.sess.host in ('localhost', socket.gethostname())
        if not(test_dir) and not (loc_server):
            self.skipTest('Requires access to server-side file(s)')
        dt=datetime.now()
        uniq1 = unique_name (my_function_name(), 1, dt)
        uniq2 = unique_name (my_function_name(), 2, dt)
        dir1 = dir2 = ''
        data_objects = []
        try:
            VAULT_MODE = (loc_server, 0o777|stat.S_ISGID)
            dir1 = make_ufs_resc_in_tmpdir(self.sess, uniq1, allow_local = loc_server, client_vault_mode = VAULT_MODE)
            dir2 = make_ufs_resc_in_tmpdir(self.sess, uniq2, allow_local = loc_server, client_vault_mode = VAULT_MODE)

            def replica_number_from_resource_name(data_path, resc):
                return [r.number for r in self.sess.data_objects.get(data_path).replicas if r.resource_name == resc][0]

            # Use two different ways to specify unregister target:
            for keyword in (kw.RESC_NAME_KW, kw.REPL_NUM_KW):
                dt=datetime.now()
                data_path = '{self.coll_path}/435_test_{dt:%s.%f}'.format(**locals())
                data = self.sess.data_objects.create(data_path, resource = uniq1)
                data_objects.append(data)

                # Ensure that two replicas exist.
                data.replicate(**{kw.DEST_RESC_NAME_KW:uniq2})
                data = self.sess.data_objects.get(data_path)
                self.assertEqual(2,len(data.replicas))

                physical_paths = [r.path for r in data.replicas]

                # Assert that unregistering the specific replica decreases the number of replicas by 1.
                data.unregister(**{keyword:(replica_number_from_resource_name(data_path, uniq2) if keyword == kw.REPL_NUM_KW else uniq2),
                                   kw.COPIES_KW:1})
                self.assertEqual(1, len(self.sess.data_objects.get(data_path).replicas))

                # Assert replica files still both on disk.
                for phys in physical_paths:
                    os.stat(phys)
        finally:
            # Clean up.
            for d in data_objects: d.unlink(force = True)
            if dir1: self.sess.resources.get(uniq1).remove()
            if dir2: self.sess.resources.get(uniq2).remove()

    def test_set_and_access_data_comments__issue_450(self):
        comment = unique_name(my_function_name(), datetime.now()) + " issue 450"
        ses = self.sess
        with self.create_simple_resc() as newResc:
            try:
                d = ses.data_objects.create('/{0.zone}/home/{0.username}/data_object_for_issue_450_test'.format(ses))
                d.replicate(**{kw.DEST_RESC_NAME_KW:newResc})
                ses.data_objects.modDataObjMeta({'objPath':d.path, 'rescHier':ses.resources.get(newResc).hierarchy_string},
                                                {'dataComments':comment})
                d = ses.data_objects.get(d.path)
                repl = [r for r in d.replicas if r.resource_name == newResc][0]
                self.assertEqual(repl.comments, comment)
            finally:
                d.unlink(force = True)

    def _auto_close_test(self, data_object_path, content):
        d = None
        try:
            d = self.sess.data_objects.get(data_object_path)
            self.assertEqual(int(d.replicas[0].status), 1)
            self.assertEqual(d.open('r').read().decode(), content)
        finally:
            if d: d.unlink(force = True)

    def test_data_objects_auto_close_on_process_exit__issue_456(self):
        program = os.path.join(test_modules.__path__[0], 'test_auto_close_of_data_objects__issue_456.py')
        # Use the currently running Python interpreter binary to run the script in the child process.
        p = subprocess.Popen([sys.executable,program], stdout=subprocess.PIPE)
        data_object_path, expected_content = p.communicate()[0].decode().split()
        self._auto_close_test(data_object_path, expected_content)

    def test_data_objects_auto_close_on_function_exit__issue_456(self):
        import irods.test.modules.test_auto_close_of_data_objects__issue_456 as test_module
        data_object_path, expected_content = test_module.test(return_locals = ('name','expected_content'))
        self._auto_close_test(data_object_path, expected_content)

    @unittest.skipIf(helpers.configuration_file_exists(),"test would overwrite pre-existing configuration.")
    def test_settings_save_and_autoload__issue_471(self):
        import irods.test.modules.test_saving_and_loading_of_settings__issue_471 as test_module
        truth = int(time.time())
        test_output = test_module.test(truth)
        self.assertEqual(test_output, str(truth))

    def test_settings_load_and_save_471(self):
        from irods import settings_path_environment_variable, get_settings_path, DEFAULT_CONFIG_PATH
        settings_path = get_settings_path()
        with helpers.file_backed_up(settings_path, require_that_file_exists = False):

            RANDOM_VALUE=int(time.time())
            config.data_objects.auto_close = RANDOM_VALUE

            # Create empty settings file.
            with open(settings_path,'w'):
                pass

            # For "silent" loading.
            load_logging_options =  {'logging_level':logging.DEBUG}

            config.load(**load_logging_options)

            # Load from empty settings should change nothing.
            self.assertTrue(config.data_objects.auto_close, RANDOM_VALUE)

            os.unlink(settings_path)
            config.load(**load_logging_options)
            # Load from nonexistent settings file should change nothing.
            self.assertTrue(config.data_objects.auto_close, RANDOM_VALUE)

            with helpers.environment_variable_backed_up(settings_path_environment_variable):
                os.environ.pop(settings_path_environment_variable,None)
                tmp_path = os.path.join(gettempdir(),'.prc')
                for i, test_path in enumerate([None, '', tmp_path]):
                    if test_path is not None:
                        os.environ[settings_path_environment_variable] = test_path
                    # Check that load and save work as expected.
                    config.data_objects.auto_close = RANDOM_VALUE - i - 1
                    saved_path = config.save()
                    # File path should be as expected.
                    self.assertEqual(saved_path, (DEFAULT_CONFIG_PATH if not test_path else test_path))
                    config.data_objects.auto_close = RANDOM_VALUE
                    config.load(**load_logging_options)
                    self.assertTrue(config.data_objects.auto_close, RANDOM_VALUE - i - 1)

if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
