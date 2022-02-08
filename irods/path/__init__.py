"""A module providing tools for path normalization and manipulation."""

__all__ = ['iRODSPath']

import re
import logging
import os

_multiple_slash = re.compile('/+')

class iRODSPath(str):
    """A subclass of the Python string that normalizes iRODS logical paths."""

    def __new__(cls, *elem_list, **kw):
        """
        Initializes our immutable string object with a normalized form.
        An instance of iRODSPath is also a `str'.

        Keywords may include only 'absolute'. The default is True, forcing a slash as
        the leading character of the resulting string.

        Variadic parameters are the path elements, strings which may name individual
        collections or sub-hierarchies (internally slash-separated).  These are then
        joined using the path separator:

            data_path = iRODSPath( 'myZone', 'home/user', './dir', 'mydata')
            # => '/myZone/home/user/dir/mydata'

        In the resulting object, any trailing and redundant path separators are removed,
        as is the "trivial" path element ('.'), so this will work:

            c = iRODSPath('/tempZone//home/./',username + '/')
            session.collections.get( c )

        If the `absolute' keyword hint is set to False, leading '..' elements are not
        suppressed (since only for absolute paths is "/.." equivalent to "/"), and the
        leading slash requirement will not be imposed on the resulting string.
        Note also that a leading slash in the first argument will be preserved regardless
        of the `absolute' hint, but subsequent arguments will act as relative paths
        regardless of leading slashes. So this will do the "right thing":

            my_dir = str(iRODSPath('dir1'))                     # => "/dir1"
            my_rel = ""+iRODSPath('dir2', absolute=False)       # => "dir2"
            my_abs = iRODSPath('/Z/home/user', my_dir, my_rel)  # => "/Z/home/user/dir1/dir2"

        Finally, because iRODSPath has `str` as a base class, this is also possible:

            iRODSPath('//zone/home/public/this', iRODSPath('../that',absolute=False))
            # => "/zone/home/public/that"
        """
        absolute_ = kw.pop('absolute',True)
        if kw:
            logging.warning("These iRODSPath options have no effect: %r",kw.items())
        normalized = cls.resolve_irods_path(*elem_list,**{"absolute":absolute_})
        obj = str.__new__(cls,normalized)
        return obj


    @staticmethod
    def resolve_irods_path(*path_elems, **kw):

        abs_ = kw['absolute']

        # Since we mean this operation to be purely a concatenation, we must strip
        # '/' from all but first path component or os.path, or os.path.join
        # will disregard all path elements preceding an absolute path specification.

        while path_elems and not path_elems[0]:
            path_elems = path_elems[1:]          # allow no leading empties preempting leading slash
        elems = list(path_elems[:1]) + [elem.lstrip("/") for elem in path_elems[1:]]
        retv = os.path.normpath(os.path.join(('/' if abs_ else ''), *elems))
        return retv if not retv.startswith('//') else retv[1:] # Grrr...: https://bugs.python.org/issue26329
