__all__ = ["pam_password", "native"]

AUTH_PLUGIN_PACKAGE = "irods.auth"

import importlib


def load_plugins(subset=set(), _reload=False):
    if not subset:
        subset = set(__all__)
    dir_ = set(globals()) & set(__all__)  # plugins already loaded
    for s in subset:
        if s not in dir_ or _reload:
            mod = importlib.import_module("." + s, package=AUTH_PLUGIN_PACKAGE)
            if _reload:
                importlib.reload(mod)
        dir_ |= {s}
    return dir_


# TODO(#499): X models a class which we could define here as a base for various server or client state machines
#             as appropriate for the various authentication types.


class X:
    pass
