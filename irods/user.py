from __future__ import absolute_import
from irods.models import User, UserGroup, UserAuth
from irods.meta import iRODSMetaCollection
from irods.exception import NoResultFound

_Not_Defined = ()

class iRODSUser(object):

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[User.id]
            self.name = result[User.name]
            self.type = result[User.type]
            self.zone = result[User.zone]
            self._comment = result.get(User.comment, _Not_Defined)  # these not needed in results for object ident,
            self._info = result.get(User.info, _Not_Defined)        # so we fetch lazily via a property
        self._meta = None

    @property
    def comment(self):
        if self._comment == _Not_Defined:
            query = self.manager.sess.query(User.id,User.comment).filter(User.id == self.id)
            self._comment = query.one()[User.comment]
        return self._comment

    @property
    def info(self):
        if self._info == _Not_Defined:
            query = self.manager.sess.query(User.id,User.info).filter(User.id == self.id)
            self._info = query.one()[User.info]
        return self._info

    @property
    def dn(self):
        query = self.manager.sess.query(UserAuth.user_dn).filter(UserAuth.user_id == self.id)
        return [res[UserAuth.user_dn] for res in query]

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(
                 self.manager.sess.metadata, User, self.name)
        return self._meta

    def modify(self, *args, **kwargs):
        self.manager.modify(self.name, *args, **kwargs)

    def __repr__(self):
        return "<iRODSUser {id} {name} {type} {zone}>".format(**vars(self))

    def remove(self):
        self.manager.remove(self.name, self.zone)


class iRODSUserGroup(object):

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[UserGroup.id]
            self.name = result[UserGroup.name]
        self._meta = None

    def __repr__(self):
        return "<iRODSUserGroup {id} {name}>".format(**vars(self))

    def remove(self):
        self.manager.remove(self.name)

    @property
    def members(self):
        return self.manager.getmembers(self.name)

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(
                 self.manager.sess.metadata, User, self.name)
        return self._meta

    def addmember(self, user_name, user_zone=""):
        self.manager.addmember(self.name, user_name, user_zone)

    def removemember(self, user_name, user_zone=""):
        self.manager.removemember(self.name, user_name, user_zone)

    def hasmember(self, user_name):
        member_names = [user.name for user in self.members]
        return user_name in member_names
