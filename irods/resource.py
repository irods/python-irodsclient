from irods.models import Resource
from irods.meta import iRODSMetaCollection


class iRODSResource:

    def __init__(self, manager, result=None):
        self._hierarchy_string = ""
        self._parent_name = ""
        self._parent_id = ""
        """
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
        """
        self.manager = manager
        if result:
            for attr, value in Resource.__dict__.items():
                if not attr.startswith("_"):
                    try:
                        setattr(self, attr, result[value])
                    except KeyError:
                        # backward compatibility with older schema versions
                        pass

        self._meta = None

    ## Cached properties to expose parent id or name regardless whether the DB model is iRODS 4.1- or 4.2+

    def modify(self, attribute, value):
        self.manager.modify(self.name, attribute, value)

    @property
    def parent_id(self):
        if self.parent is None:
            return None
        if self._parent_id == "":
            sess = self.manager.sess
            if sess.server_version >= (4, 2, 0):
                self._parent_id = self.parent
            else:
                self._parent_id = (
                    sess.query(Resource)
                    .filter(Resource.name == self.parent)
                    .one()[Resource.id]
                )
        return int(self._parent_id)

    @property
    def parent_name(self):
        if self.parent is None:
            return None
        if self._parent_name == "":
            sess = self.manager.sess
            if sess.server_version < (4, 2, 0):
                self._parent_name = self.parent
            else:
                self._parent_name = (
                    sess.query(Resource)
                    .filter(Resource.id == self.parent)
                    .one()[Resource.name]
                )
        return self._parent_name

    ## Cached property to expose resource hierarchy string

    @property
    def hierarchy_string(self):
        if self._hierarchy_string == "":
            self._hierarchy_string = ";".join(
                r.name for r in self.hierarchy_as_list_of_resource_objects()
            )
        return self._hierarchy_string

    ## Retrieve chain of parent objects to top level parent

    def hierarchy_as_list_of_resource_objects(self):
        trace_to_root = [self]
        sess = self.manager.sess
        r = self.parent_id
        while r is not None:
            parent = sess.query(Resource).filter(Resource.id == r).one()
            trace_to_root.append(iRODSResource(self.manager, parent))
            r = trace_to_root[-1].parent_id
        return list(reversed(trace_to_root))

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(
                self.manager.sess.metadata, Resource, self.name
            )
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

            if version >= (4, 2, 0):
                # iRODS 4.2+: find parent by resource id
                parent = self.id
            elif version >= (4, 0, 0):
                # iRODS 4.0/4.1: find parent by resource name
                parent = self.name
            else:
                raise RuntimeError("Resource composition not supported")

            # query for children and cache results
            query = session.query(Resource).filter(
                Resource.parent == "{}".format(parent)
            )
            self._children = [self.__class__(self.manager, res) for res in query]

            return self._children

    @children.setter
    def children(self, children):
        pass

    def __repr__(self):
        return "<iRODSResource {id} {name} {type}>".format(**vars(self))

    def remove(self, test=False):
        self.manager.remove(self.name, test)
