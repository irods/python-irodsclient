from __future__ import absolute_import
from irods.models import Zone


class iRODSZone(object):

    def __init__(self, manager, result=None):
        """Construct an iRODSZone object."""
        self.manager = manager
        if result:
            self.id = result[Zone.id]
            self.name = result[Zone.name]
            self.type = result[Zone.type]

    def remove(self):
        self.manager.remove(self.name)

    def __repr__(self):
        """Render a user-friendly string representation for the iRODSZone object."""
        return "<iRODSZone {id} {name} {type}>".format(**vars(self))

