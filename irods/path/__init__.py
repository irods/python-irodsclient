"""A module providing tools for path normalization and manipulation."""

__all__ = ["iRODSPath"]

import re
import logging
import os


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
        absolute_ = kw.pop("absolute", True)
        if kw:
            logging.warning("These iRODSPath options have no effect: %r", kw.items())
        normalized = _normalize_iRODS_logical_path(elem_list, absolute_)
        obj = str.__new__(cls, normalized)
        return obj


def _normalize_iRODS_logical_path(paths, make_absolute):
    build = []

    if paths and paths[0][:1] == "/":
        make_absolute = True

    p = "/".join(paths).split("/")

    while p and not p[0]:
        p.pop(0)

    prefixed_updirs = 0

    # Break out and resolve updir('..') and trivial path elements like '.', ''

    for elem in p:
        if elem == "..":
            if not build:
                prefixed_updirs += 0 if make_absolute else 1
            else:
                if build[-1]:
                    build.pop()
            continue
        elif elem in ("", "."):
            continue
        build.append(elem)

    # Restore any initial updirs
    build[:0] = [".."] * prefixed_updirs

    # Rejoin components, respecting 'make_absolute' flag
    path_ = ("/" if make_absolute else "") + "/".join(build)

    # Empty path equivalent to "current directory"
    return "." if not path_ else path_
