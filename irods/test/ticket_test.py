#! /usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import unittest
import time
import calendar

import irods.test.helpers as helpers
import tempfile
from irods.session import iRODSSession
import irods.exception as ex
import irods.keywords as kw
from irods.ticket import Ticket
from irods.models import (TicketQuery,DataObject,Collection)


# As with most of the modules in this test suite, session objects created via
# make_session() are implicitly agents of a rodsadmin unless otherwise indicated.
# Counterexamples within this module shall be obvious as they are instantiated by
# the login() method, and always tied to one of the traditional rodsuser names
# widely used in iRODS test suites, ie. 'alice' or 'bob'.


def gmtime_to_timestamp (gmt_struct):
    return "{0.tm_year:04d}-{0.tm_mon:02d}-{0.tm_mday:02d}."\
           "{0.tm_hour:02d}:{0.tm_min:02d}:{0.tm_sec:02d}".format(gmt_struct)


def delete_my_tickets(session):
    my_userid = session.users.get( session.username ).id
    my_tickets = session.query(TicketQuery.Ticket).filter(TicketQuery.Ticket.user_id ==  my_userid)
    for res in my_tickets:
        Ticket(session, result = res).delete()


class TestRodsUserTicketOps(unittest.TestCase):

    def login(self,user):
        return iRODSSession (port=self.port,zone=self.zone,host=self.host,
                user=user.name,password=self.users[user.name])

    @staticmethod
    def irods_homedir(sess, path_only = False):
        path = '/{0.zone}/home/{0.username}'.format(sess)
        if path_only:
            return path
        return sess.collections.get(path)

    @staticmethod
    def list_objects (sess):
        return [ '{}/{}'.format(o[Collection.name],o[DataObject.name]) for o in
            sess.query(Collection.name,DataObject.name) ]

    users = {
            'alice':'apass',
            'bob':'bpass'
            }

    def setUp(self):

        self.alice = self.bob = None

        with helpers.make_session() as ses:
            u = ses.users.get(ses.username)
            if u.type != 'rodsadmin':
                self.skipTest('''Test runnable only by rodsadmin.''')
            self.host = ses.host
            self.port = ses.port
            self.zone = ses.zone
            for newuser,passwd in self.users.items():
                u = ses.users.create( newuser, 'rodsuser')
                setattr(self,newuser,u)
                u.modify('password', passwd)

    def tearDown(self):
        with helpers.make_session() as ses:
            for u in self.users:
                ses.users.remove(u)


    def test_admin_keyword_for_tickets (self):

        N_TICKETS = 3

        # Create some tickets as alice.

        with self.login(self.alice) as alice:
            alice_home_path = self.irods_homedir(alice, path_only = True)
            ticket_strings = [ Ticket(alice).issue('read', alice_home_path).string for _ in range(N_TICKETS) ]

        # As rodsadmin, use the ADMIN_KW flag to delete alice's tickets.

        with helpers.make_session() as ses:
            alices_tickets = [t[TicketQuery.Ticket.string] for t in ses.query(TicketQuery.Ticket).filter(TicketQuery.Owner.name == 'alice')]
            self.assertEqual(len(alices_tickets),N_TICKETS)
            for s in alices_tickets:
                Ticket( ses, s ).delete(**{kw.ADMIN_KW:''})
            alices_tickets = [t[TicketQuery.Ticket.string] for t in ses.query(TicketQuery.Ticket).filter(TicketQuery.Owner.name == 'alice')]
            self.assertEqual(len(alices_tickets),0)


    def test_ticket_expiry (self):
        with helpers.make_session() as ses:
            t1 = t2 = dobj = None
            try:
                gm_now = time.gmtime()
                gm_later = time.gmtime( calendar.timegm( gm_now ) + 10 )
                home = self.irods_homedir(ses)
                dobj = helpers.make_object(ses, home.path+'/dummy', content='abcxyz')

                later_ts = gmtime_to_timestamp (gm_later)
                later_epoch = calendar.timegm (gm_later)

                t1 = Ticket(ses)
                t2 = Ticket(ses)

                tickets = [ _.issue('read',dobj.path).string for _ in (t1,
                                                                       t2,) ]
                t1.modify('expire',later_ts)    # - Specify expiry with the human readable timestamp.
                t2.modify('expire',later_epoch) # - Specify expiry formatted as epoch seconds.

                # Check normal access succeeds prior to expiration
                for ticket_string in tickets:
                    with self.login(self.alice) as alice:
                        Ticket(alice, ticket_string).supply()
                        alice.data_objects.get(dobj.path)

                # Check that both time formats have effected the same expiry time (The catalog returns epoch secs.)
                timestamps = []
                for ticket_string in tickets:
                    t = ses.query(TicketQuery.Ticket).filter(TicketQuery.Ticket.string == ticket_string).one()
                    timestamps.append( t [TicketQuery.Ticket.expiry_ts] )
                self.assertEqual (len(timestamps),2)
                self.assertEqual (timestamps[0],timestamps[1])

                # Wait for tickets to expire.
                epoch = int(time.time())
                while epoch <= later_epoch:
                    time.sleep(later_epoch - epoch + 1)
                    epoch = int(time.time())

                Expected_Exception = ex.CAT_TICKET_EXPIRED if ses.server_version >= (4,2,9) \
                        else ex.SYS_FILE_DESC_OUT_OF_RANGE

                # Check tickets no longer allow access.
                for ticket_string in tickets:
                    with self.login(self.alice) as alice, tempfile.NamedTemporaryFile() as f:
                        Ticket(alice, ticket_string).supply()
                        with self.assertRaises( Expected_Exception ):
                            alice.data_objects.get(dobj.path,f.name, **{kw.FORCE_FLAG_KW:''})

            finally:
                if t1: t1.delete()
                if t2: t2.delete()
                if dobj: dobj.unlink(force=True)


    def test_object_read_and_write_tickets(self):
        if self.alice is None or self.bob is None:
            self.skipTest("A rodsuser (alice and/or bob) could not be created.")
        t=None
        data_objs=[]
        tmpfiles=[]
        try:
            # Create ticket for read access to alice's home collection.
            alice = self.login(self.alice)
            home = self.irods_homedir(alice)

            # Create 'R' and 'W' in alice's home collection.
            data_objs = [helpers.make_object(alice,home.path+"/"+name,content='abcxyz') for name in ('R','W')]
            tickets = {
                'R': Ticket(alice).issue('read',  home.path + "/R").string,
                'W': Ticket(alice).issue('write', home.path + "/W").string
            }
            # Test only write ticket allows upload.
            with self.login(self.bob) as bob:
                rw_names={}
                for name in  ('R','W'):
                    Ticket( bob, tickets[name] ).supply()
                    with tempfile.NamedTemporaryFile (delete=False) as tmpf:
                        tmpfiles += [tmpf]
                        rw_names[name] = tmpf.name
                        tmpf.write(b'hello')
                    if name=='W':
                        bob.data_objects.put(tmpf.name,home.path+"/"+name)
                    else:
                        try:
                            bob.data_objects.put(tmpf.name,home.path+"/"+name)
                        except ex.CAT_NO_ACCESS_PERMISSION:
                            pass
                        else:
                            raise AssertionError("A read ticket allowed a data object write operation to happen without error.")

            # Test upload was successful, by getting and confirming contents.

            with self.login(self.bob) as bob:  # This check must be in a new session or we get CollectionDoesNotExist. - Possibly a new issue [ ]
                for name in  ('R','W'):
                    Ticket( bob, tickets[name] ).supply()
                    bob.data_objects.get(home.path+"/"+name,rw_names[ name ],**{kw.FORCE_FLAG_KW:''})
                    with open(rw_names[ name ],'r') as tmpread:
                        self.assertEqual(tmpread.read(),
                                         'abcxyz' if name == 'R' else 'hello')
        finally:
            if t: t.delete()
            for d in data_objs:
                d.unlink(force=True)
            for file_ in tmpfiles: os.unlink( file_.name )
            alice.cleanup()


    def test_coll_read_ticket_between_rodsusers(self):
        t=None
        data_objs=[]
        tmpfiles=[]
        try:
            # Create ticket for read access to alice's home collection.
            alice = self.login(self.alice)
            tc = Ticket(alice)
            home = self.irods_homedir(alice)
            tc.issue('read', home.path)

            # Create 'x' and 'y' in alice's home collection
            data_objs = [helpers.make_object(alice,home.path+"/"+name,content='abcxyz') for name in ('x','y')]

            with self.login(self.bob) as bob:
                ts = Ticket( bob, tc.string )
                ts.supply()
                # Check collection access ticket allows bob to list both subobjects
                self.assertEqual(len(self.list_objects(bob)),2)
                # and that we can get (and read) them properly.
                for name in ('x','y'):
                    with tempfile.NamedTemporaryFile (delete=False) as tmpf:
                        tmpfiles += [tmpf]
                    bob.data_objects.get(home.path+"/"+name,tmpf.name,**{kw.FORCE_FLAG_KW:''})
                    with open(tmpf.name,'r') as tmpread:
                        self.assertEqual(tmpread.read(),'abcxyz')

            td = Ticket(alice)
            td.issue('read', home.path+"/x")

            with self.login(self.bob) as bob:
                ts = Ticket( bob, td.string )
                ts.supply()

                # Check data access ticket allows bob to list only one data object
                self.assertEqual(len(self.list_objects(bob)),1)

                # ... and fetch that object (verifying content)
                with tempfile.NamedTemporaryFile (delete=False) as tmpf:
                    tmpfiles += [tmpf]
                bob.data_objects.get(home.path+"/x",tmpf.name,**{kw.FORCE_FLAG_KW:''})
                with open(tmpf.name,'r') as tmpread:
                    self.assertEqual(tmpread.read(),'abcxyz')

                # ... but not fetch the other data object owned by alice.
                with self.assertRaises(ex.DataObjectDoesNotExist):
                    bob.data_objects.get(home.path+"/y")
        finally:
            if t: t.delete()
            for d in data_objs:
                d.unlink(force=True)
            for file_ in tmpfiles: os.unlink( file_.name )
            alice.cleanup()


class TestTicketOps(unittest.TestCase):

    def setUp(self):
        """Create objects for test"""
        self.sess = helpers.make_session()
        user = self.sess.users.get(self.sess.username)
        if user.type != 'rodsadmin':
            self.skipTest('''Test runnable only by rodsadmin.''')

        admin = self.sess
        delete_my_tickets( admin )

        # Create test collection

        self.coll_path = '/{}/home/{}/ticket_test_dir'.format(admin.zone, admin.username)
        self.coll = helpers.make_collection(admin, self.coll_path)

        # Create anonymous test user
        self.user = admin.users.create('anonymous','rodsuser')
        self.rodsuser_params = { 'host':admin.host,
                                 'port':admin.port,
                                 'user': 'anonymous',
                                 'password':'',
                                 'zone':admin.zone }

        # make new data object in the test collection with some initialized content

        self.INITIALIZED_DATA = b'1'*16
        self.data_path = '{self.coll_path}/ticketed_data'.format(**locals())
        helpers.make_object (admin, self.data_path, content = self.INITIALIZED_DATA)

        self.MODIFIED_DATA = b'2'*16

        # make new tickets for the various combinations

        self.tickets = {'coll':{},'data':{}}
        for obj_type in ('coll','data'):
            for access in ('read','write'):
                ticket = Ticket(admin)
                self.tickets [obj_type] [access] = ticket.string
                ticket.issue( access , getattr(self, obj_type + '_path'))


    def tearDown(self):
        """Clean up tickets , collections and data objects used for test."""
        admin = self.sess
        delete_my_tickets( admin )
        if getattr(self,'coll',None):
            self.coll.remove(recurse=True, force=True)
        if getattr(self,'user',None):
            self.user.remove()
        admin.cleanup()


    def _ticket_read_helper( self, obj_type, download = False ):
        with iRODSSession( ** self.rodsuser_params ) as user_sess:
            temp_file = []
            if download: temp_file += [tempfile.mktemp()]
            try:
                Ticket(user_sess, self.tickets[obj_type]['read']).supply()
                data = user_sess.data_objects.get(self.data_path,*temp_file)
                self.assertEqual (data.open('r').read(), self.INITIALIZED_DATA)
                if temp_file:
                    with open(temp_file[0],'rb') as local_file:
                        self.assertEqual (local_file.read(), self.INITIALIZED_DATA)
            finally:
                if temp_file and os.path.exists(temp_file[0]):
                    os.unlink(temp_file[0])


    def test_data_ticket_read(self): self._ticket_read_helper( obj_type = 'data' )

    def test_coll_ticket_read(self): self._ticket_read_helper( obj_type = 'coll' )

    def test_data_ticket_read_with_download(self): self._ticket_read_helper( obj_type = 'data', download = True )

    def test_coll_ticket_read_with_download(self): self._ticket_read_helper( obj_type = 'coll', download = True )


    def _ticket_write_helper( self, obj_type ):
        with iRODSSession( ** self.rodsuser_params ) as user_sess:
            Ticket(user_sess, self.tickets[obj_type]['write']).supply()
            data = user_sess.data_objects.get(self.data_path)
            with data.open('w') as obj:
                obj.write(self.MODIFIED_DATA)
            self.assertEqual (data.open('r').read(), self.MODIFIED_DATA)


    def test_data_ticket_write(self): self._ticket_write_helper( obj_type = 'data' )

    def test_coll_ticket_write(self): self._ticket_write_helper( obj_type = 'coll' )


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
