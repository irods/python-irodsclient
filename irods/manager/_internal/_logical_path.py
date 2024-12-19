from irods.exception import CollectionDoesNotExist


def _is_collection(session, path):
    """Return True if the logical path points to a collection, else False.

    Parameters
    ----------
    session: iRODSSession
        The session object.

    path: string
        The absolute logical path to a collection.
    """
    try:
        session.collections.get(path)
        return True
    except CollectionDoesNotExist:
        pass
    return False
