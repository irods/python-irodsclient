from irods.models import User, Group, UserAuth
from irods.meta import iRODSMetaCollection
from irods.exception import NoResultFound

_Not_Defined = ()


class Bad_password_change_parameter(Exception):
    pass


class iRODSUser:

    def remove_quota(self, resource="total"):
        self.manager.remove_quota(self.name, resource=resource)

    # TODO: remove this in branch 2.x (#482)
    def set_quota(self, amount, resource="total"):
        self.manager.set_quota(self.name, amount, resource=resource)

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[User.id]
            self.name = result[User.name]
            self.type = result[User.type]
            self.zone = result[User.zone]
            self._comment = result.get(
                User.comment, _Not_Defined
            )  # these not needed in results for object ident,
            self._info = result.get(
                User.info, _Not_Defined
            )  # so we fetch lazily via a property
        self._meta = None

    @property
    def comment(self):
        if self._comment == _Not_Defined:
            query = self.manager.sess.query(User.id, User.comment).filter(
                User.id == self.id
            )
            self._comment = query.one()[User.comment]
        return self._comment

    @property
    def info(self):
        if self._info == _Not_Defined:
            query = self.manager.sess.query(User.id, User.info).filter(
                User.id == self.id
            )
            self._info = query.one()[User.info]
        return self._info

    @property
    def dn(self):
        query = self.manager.sess.query(UserAuth.user_dn).filter(
            UserAuth.user_id == self.id
        )
        return [res[UserAuth.user_dn] for res in query]

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(
                self.manager.sess.metadata, User, self.name
            )
        return self._meta

    def modify_password(
        self, old_value, new_value, modify_irods_authentication_file=False
    ):
        self.manager.modify_password(
            old_value,
            new_value,
            modify_irods_authentication_file=modify_irods_authentication_file,
        )

    def modify(self, *args, **kwargs):
        self.manager.modify(self.name, *args, **kwargs)

    def __repr__(self):
        return f"<iRODSUser {self.id} {self.name} {self.type} {self.zone}>"

    def remove(self):
        self.manager.remove(self.name, self.zone, _object=self)

    def temp_password(self):
        return self.manager.temp_password_for_user(self.name)


class iRODSGroup:

    type = "rodsgroup"

    def remove_quota(self, resource="total"):
        self.set_quota(amount=0, resource=resource)

    def set_quota(self, amount, resource="total"):
        self.manager.set_quota(self.name, amount, resource=resource)

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[Group.id]
            self.name = result[Group.name]
        self._meta = None

    def __repr__(self):
        return f"<iRODSGroup {self.id} {self.name}>"

    def remove(self):
        self.manager.remove(self.name, _object=self)

    @property
    def members(self):
        return self.manager.getmembers(self.name)

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(
                self.manager.sess.metadata, User, self.name
            )
        return self._meta

    def addmember(self, user_name, user_zone=""):
        self.manager.addmember(self.name, user_name, user_zone)

    def removemember(self, user_name, user_zone=""):
        self.manager.removemember(self.name, user_name, user_zone)

    def hasmember(self, user_name):
        member_names = [user.name for user in self.members]
        return user_name in member_names


# The iRODSUserGroup is now renamed iRODSGroup, but we'll keep the deprecated name around for now.
iRODSUserGroup = iRODSGroup
