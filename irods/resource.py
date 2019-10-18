from __future__ import absolute_import
from irods.models import Resource
from irods.meta import iRODSMetaCollection
import six


class iRODSResource(object):

    def __init__(self, manager, result=None):
        '''
        self.id = result[Resource.id]
        self.name = result[Resource.name]
        self.zone_name = result[Resource.zone_name]
        self.type = result[Resource.type]
        self.class_name = result[Resource.class_name]
        self.location = result[Resource.location]
        self.vault_path = result[Resource.vault_path]
        self.free_space = result[Resource.free_space]
        self.free_space_time = result[Resource.free_space_time]
        self.comment = result[Resource.comment]
        self.create_time = result[Resource.create_time]
        self.modify_time = result[Resource.modify_time]
        self.status = result[Resource.status]
        self.children = result[Resource.children]
        self.context = result[Resource.context]
        self.parent = result[Resource.parent]
        self.parent_context = result[Resource.parent_context]
        '''
        self.manager = manager
        if result:
            for attr, value in six.iteritems(Resource.__dict__):
                if not attr.startswith('_'):
                    try:
                        setattr(self, attr, result[value])
                    except KeyError:
                        # backward compatibility with older schema versions
                        pass

        self._meta = None

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(
                self.manager.sess.metadata, Resource, self.name)
        return self._meta

    @property
    def context_fields(self):
        return dict(pair.split("=") for pair in self.context.split(";"))


    @property
    def children(self):
        try:
            return self._children
        except AttributeError:
            # the children have not yet been resolved
            session = self.manager.sess
            version = session.server_version

            if version >= (4,2,0):
                # iRODS 4.2+: find parent by resource id
                parent = self.id
            elif version >= (4,0,0):
                # iRODS 4.0/4.1: find parent by resource name
                parent = self.name
            else:
                raise RuntimeError('Resource composition not supported')

            # query for children and cache results
            query = session.query(Resource).filter(Resource.parent == '{}'.format(parent))
            self._children = [self.__class__(self.manager, res) for res in query]

            return self._children


    @children.setter
    def children(self, children):
        pass


    def __repr__(self):
        return "<iRODSResource {id} {name} {type}>".format(**vars(self))


    def remove(self, test=False):
        self.manager.remove(self.name, test)
