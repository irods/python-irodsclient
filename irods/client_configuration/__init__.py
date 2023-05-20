from __future__ import print_function
import ast
import copy
import io
import logging
import re
import sys
import types

logger = logging.Logger(__name__)

class iRODSConfiguration(object):
    __slots__ = ()

def getter(category, setting):
    return lambda:getattr(globals()[category], setting)

# #############################################################################
#
# Classes for building client configuration categories
# (irods.client_configuration.data_objects is one such category):

class DataObjects(iRODSConfiguration):
    __slots__ = ('auto_close',)

    def __init__(self):

        # Setting it in the constructor lets the attribute be a
        # configurable one and allows a default value of False.
        #
        # Running following code will opt in to the the auto-closing
        # behavior for any data objects opened subsequently.
        #
        # >>> import irods.client_configuration as config
        # >>> irods.client_configuration.data_objects.auto_close = True

        self.auto_close = False

# #############################################################################
#
# Instantiations of client-configuration categories:

# The usage "irods.client_configuration.data_objects" reflects the commonly used
# manager name (session.data_objects) and is thus understood to influence the
# behavior of data objects.
#
# By design, valid configurable targets (e.g. auto_close) are limited to the names
# listed in the __slots__ member of the category class.

data_objects = DataObjects()
