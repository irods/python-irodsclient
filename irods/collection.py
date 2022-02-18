from __future__ import absolute_import
import itertools
import operator

from irods.models import Collection, DataObject
from irods.data_object import iRODSDataObject, irods_basename
from irods.meta import iRODSMetaCollection

def _first_char( *Strings ):
    for s in Strings:
        if s: return s[0]
    return ''

class iRODSCollection(object):

    class AbsolutePathRequired(Exception):
        """Exception raised by iRODSCollection.normalize_path.

        AbsolutePathRequired is raised by normalize_path( *paths ) when the leading path element
        does not start with '/'.  The exception will not be raised, however, if enforce_absolute = False
        is passed to normalize_path as a keyword option.
        """
        pass

    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[Collection.id]
            self.path = result[Collection.name]
            self.name = irods_basename(result[Collection.name])
            self.create_time = result[Collection.create_time]
            self.modify_time = result[Collection.modify_time]
            self._inheritance = result[Collection.inheritance]
            self.owner_name = result[Collection.owner_name]
            self.owner_zone = result[Collection.owner_zone]
        self._meta = None

    @property
    def inheritance(self):
        return bool(self._inheritance) and self._inheritance != "0"

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(self.manager.sess.metadata,
                                             Collection, self.path)
        return self._meta

    @property
    def subcollections(self):
        query = self.manager.sess.query(Collection)\
            .filter(Collection.parent_name == self.path)
        return [iRODSCollection(self.manager, row) for row in query]

    @property
    def data_objects(self):
        query = self.manager.sess.query(DataObject)\
            .filter(Collection.name == self.path)
        results = query.get_results()
        grouped = itertools.groupby(
            results, operator.itemgetter(DataObject.id))
        return [
            iRODSDataObject(
                self.manager.sess.data_objects, self, list(replicas))
            for _, replicas in grouped
        ]

    def remove(self, recurse=True, force=False, **options):
        self.manager.remove(self.path, recurse, force, **options)

    def unregister(self, **options):
        self.manager.unregister(self.path, **options)

    def move(self, path):
        self.manager.move(self.path, path)

    def walk(self, topdown=True):
        """
        Collection tree generator.

        For each subcollection in the directory tree, starting at the
        collection, yield a 3-tuple
        """

        if topdown:
            yield (self, self.subcollections, self.data_objects)
        for subcollection in self.subcollections:
            new_root = subcollection
            for x in new_root.walk(topdown):
                yield x
        if not topdown:
            yield (self, self.subcollections, self.data_objects)

    @staticmethod
    def normalize_path(*paths, **kw_):
        """Normalize a path or list of paths.

        We use the iRODSPath class to eliminate extra slashes in,
        and (if more than one parameter is given) concatenate, paths.
        If the keyword argument `enforce_absolute' is set True, this
        function requires the first character of path(s) passed in
        should be '/'.
        """
        import irods.path
        absolute = kw_.get('enforce_absolute',False)
        if absolute and _first_char(*paths) != '/':
            raise iRODSCollection.AbsolutePathRequired
        return irods.path.iRODSPath(*paths, absolute = absolute)

    def __repr__(self):
        return "<iRODSCollection {id} {name}>".format(id = self.id, name = self.name.encode('utf-8'))
