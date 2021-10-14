from __future__ import absolute_import
from irods.column import Column, Integer, String, DateTime, Keyword
import six


class ModelBase(type):
    columns = {}

    def __new__(cls, name, bases, attr):
        columns = [y for (x, y) in six.iteritems(attr) if isinstance(y, Column)]
        for col in columns:
            ModelBase.columns[col.icat_id] = col
        attr['_columns'] = columns
        # attr['_icat_column_names'] = [y.icat_key for (x,y) in columns]
        return type.__new__(cls, name, bases, attr)


class Model(six.with_metaclass(ModelBase, object)):
    pass


class RuleExec(Model):
    id = Column(Integer, 'RULE_EXEC_ID', 1000)
    name = Column(String, 'RULE_EXEC_NAME', 1001)
    rei_file_path = Column(String,'RULE_EXEC_REI_FILE_PATH', 1002)
    user_name = Column(String, 'RULE_EXEC_USER_NAME', 1003)
    time = Column(DateTime,'RULE_EXEC_TIME',    1005)
    last_exe_time = Column(DateTime,'RULE_EXEC_LAST_EXE_TIME', 1010)
    frequency = Column(String,'RULE_EXEC_FREQUENCY', 1006)
    priority = Column(String, 'RULE_EXEC_PRIORITY', 1007)

#   # If needed in 4.2.9, we can update the Query class to dynamically
#   #  attach this field based on server version:
#   context = Column(String, 'RULE_EXEC_CONTEXT', 1012)

#   # These are either unused or usually absent:
#   exec_status = Column(String,'RULE_EXEC_STATUS', 1011)
#   address = Column(String,'RULE_EXEC_ADDRESS', 1004)
#   notification_addr = Column('RULE_EXEC_NOTIFICATION_ADDR', 1009)


class Zone(Model):
    id = Column(Integer, 'ZONE_ID', 101)
    name = Column(String, 'ZONE_NAME', 102)
    type = Column(String, 'ZONE_TYPE', 103)


class User(Model):
    id = Column(Integer, 'USER_ID', 201)
    name = Column(String, 'USER_NAME', 202)
    type = Column(String, 'USER_TYPE', 203)
    zone = Column(String, 'USER_ZONE', 204)
    info = Column(String, 'USER_INFO', 206)
    comment = Column(String, 'USER_COMMENT', 207)
    create_time = Column(DateTime, 'USER_CREATE_TIME', 208)
    modify_time = Column(DateTime, 'USER_MODIFY_TIME', 209)


class UserAuth(Model):
    user_id = Column(Integer, 'USER_AUTH_ID', 1600)
    user_dn = Column(String, 'USER_DN', 1601)


class CollectionUser(Model):
    name = Column(String, 'COL_COLL_USER_NAME', 1300)
    zone = Column(String, 'COL_COLL_USER_ZONE', 1301)


class UserGroup(Model):
    id = Column(Integer, 'USER_GROUP_ID', 900)
    name = Column(String, 'USER_GROUP_NAME', 901)


class Resource(Model):
    id = Column(Integer, 'R_RESC_ID', 301)
    name = Column(String, 'R_RESC_NAME', 302)
    zone_name = Column(String, 'R_ZONE_NAME', 303)
    type = Column(String, 'R_TYPE_NAME', 304)
    class_name = Column(String, 'R_CLASS_NAME', 305)
    location = Column(String, 'R_LOC', 306)
    vault_path = Column(String, 'R_VAULT_PATH', 307)
    free_space = Column(String, 'R_FREE_SPACE', 308)
    free_space_time = Column(String, 'R_FREE_SPACE_TIME', 314, min_version=(4,0,0))
    comment = Column(String, 'R_RESC_COMMENT', 310)
    create_time = Column(DateTime, 'R_CREATE_TIME', 311)
    modify_time = Column(DateTime, 'R_MODIFY_TIME', 312)
    status = Column(String, 'R_RESC_STATUS', 313, min_version=(4,0,0))
    children = Column(String, 'R_RESC_CHILDREN', 315, min_version=(4,0,0))
    context = Column(String, 'R_RESC_CONTEXT', 316, min_version=(4,0,0))
    parent = Column(String, 'R_RESC_PARENT', 317, min_version=(4,0,0))
    parent_context = Column(String, 'R_RESC_PARENT_CONTEXT', 318, min_version=(4,2,0))


class DataObject(Model):
    id = Column(Integer, 'D_DATA_ID', 401)
    collection_id = Column(Integer, 'D_COLL_ID', 402)
    name = Column(String, 'DATA_NAME', 403)  # basename
    replica_number = Column(Integer, 'DATA_REPL_NUM', 404)
    version = Column(String, 'DATA_VERSION', 405)
    type = Column(String, 'DATA_TYPE_NAME', 406)
    size = Column(Integer, 'DATA_SIZE', 407)
    resource_name = Column(String, 'D_RESC_NAME', 409)
    path = Column(String, 'D_DATA_PATH', 410)  # physical path on resource
    owner_name = Column(String, 'D_OWNER_NAME', 411)
    owner_zone = Column(String, 'D_OWNER_ZONE', 412)
    replica_status = Column(String, 'D_REPL_STATUS', 413)
    status = Column(String, 'D_DATA_STATUS', 414)
    checksum = Column(String, 'D_DATA_CHECKSUM', 415)
    expiry = Column(String, 'D_EXPIRY', 416)
    map_id = Column(Integer, 'D_MAP_ID', 417)
    comments = Column(String, 'D_COMMENTS', 418)
    create_time = Column(DateTime, 'D_CREATE_TIME', 419)
    modify_time = Column(DateTime, 'D_MODIFY_TIME', 420)
    resc_hier = Column(String, 'D_RESC_HIER', 422, min_version=(4,0,0))
    resc_id = Column(String, 'D_RESC_ID', 423, min_version=(4,2,0))


class Collection(Model):
    id = Column(Integer, 'COLL_ID', 500)
    name = Column(String, 'COLL_NAME', 501)
    parent_name = Column(String, 'COLL_PARENT_NAME', 502)
    owner_name = Column(String, 'COLL_OWNER_NAME', 503)
    owner_zone = Column(String, 'COLL_OWNER_ZONE', 504)
    map_id = Column(String, 'COLL_MAP_ID', 505)
    inheritance = Column(String, 'COLL_INHERITANCE', 506)
    comments = Column(String, 'COLL_COMMENTS', 507)
    create_time = Column(DateTime, 'COLL_CREATE_TIME', 508)
    modify_time = Column(DateTime, 'COLL_MODIFY_TIME', 509)


class DataObjectMeta(Model):
    id = Column(String, 'COL_META_DATA_ATTR_ID', 603)
    name = Column(String, 'COL_META_DATA_ATTR_NAME', 600)
    value = Column(String, 'COL_META_DATA_ATTR_VALUE', 601)
    units = Column(String, 'COL_META_DATA_ATTR_UNITS', 602)
    create_time = Column(DateTime, 'COL_META_DATA_CREATE_TIME', 604)
    modify_time = Column(DateTime, 'COL_META_DATA_MODIFY_TIME', 605)


class CollectionMeta(Model):
    id = Column(String, 'COL_META_COLL_ATTR_UNITS', 613)
    name = Column(String, 'COL_META_COLL_ATTR_NAME', 610)
    value = Column(String, 'COL_META_COLL_ATTR_VALUE', 611)
    units = Column(String, 'COL_META_COLL_ATTR_UNITS', 612)
    create_time = Column(DateTime, 'COL_META_COLL_CREATE_TIME', 614)
    modify_time = Column(DateTime, 'COL_META_COLL_MODIFY_TIME', 615)



class ResourceMeta(Model):
    id = Column(String, 'COL_META_RESC_ATTR_UNITS', 633)
    name = Column(String, 'COL_META_RESC_ATTR_NAME', 630)
    value = Column(String, 'COL_META_RESC_ATTR_VALUE', 631)
    units = Column(String, 'COL_META_RESC_ATTR_UNITS', 632)
    create_time = Column(DateTime, 'COL_META_RESC_CREATE_TIME', 634)
    modify_time = Column(DateTime, 'COL_META_RESC_MODIFY_TIME', 635)



class UserMeta(Model):
    id = Column(String, 'COL_META_USER_ATTR_ID', 643)
    name = Column(String, 'COL_META_USER_ATTR_NAME', 640)
    value = Column(String, 'COL_META_USER_ATTR_VALUE', 641)
    units = Column(String, 'COL_META_USER_ATTR_UNITS', 642)
    create_time = Column(DateTime, 'COL_META_USER_CREATE_TIME', 644)
    modify_time = Column(DateTime, 'COL_META_USER_MODIFY_TIME', 645)



class DataAccess(Model):
    type = Column(Integer, 'DATA_ACCESS_TYPE', 700)
    name = Column(String, 'COL_DATA_ACCESS_NAME', 701)
    token_namespace = Column(String, 'COL_DATA_TOKEN_NAMESPACE', 702)
    user_id = Column(Integer, 'COL_DATA_ACCESS_USER_ID', 703)
    data_id = Column(Integer, 'COL_DATA_ACCESS_DATA_ID', 704)


class CollectionAccess(Model):
    type = Column(Integer, 'COL_COLL_ACCESS_TYPE', 710)
    name = Column(String, 'COL_COLL_ACCESS_NAME', 711)
    token_namespace = Column(String, 'COL_COLL_TOKEN_NAMESPACE', 712)
    user_id = Column(Integer, 'COL_COLL_ACCESS_USER_ID', 713)
    access_id = Column(Integer, 'COL_COLL_ACCESS_COLL_ID', 714)


class SpecificQueryResult(Model):
    '''
    To parse results of specific queries. No corresponding iCAT table.
    '''
    value = Column(String, 'SQL_RESULT_VALUE', 0)


# not really a model. Should be dict instead?
class Keywords(Model):
    data_type = Keyword(String, 'dataType')
    chksum = Keyword(String, 'chksum')


class TicketQuery:
    """Various model classes for querying attributes of iRODS tickets.

    Namespacing these model classes under the TicketQuery parent class allows
    a simple import (not conflicting with irods.ticket.Ticket) and a usage
    that reflects ICAT table structure:

        from irods.models import TicketQuery
        # ...
        for row in session.query( TicketQuery.Ticket )\
                          .filter( TicketQuery.Owner.name == 'alice' ):
            print( row [TicketQuery.Ticket.string] )

    (For more examples, see irods/test/ticket_test.py)

    """
    class Ticket(Model):
        """For queries of R_TICKET_MAIN."""
        id = Column(Integer, 'TICKET_ID', 2200)
        string = Column(String, 'TICKET_STRING', 2201)
        type = Column(String, 'TICKET_TYPE', 2202)
        user_id = Column(Integer, 'TICKET_USER_ID', 2203)
        object_id = Column(Integer, 'TICKET_OBJECT_ID', 2204)
        object_type = Column(String, 'TICKET_OBJECT_TYPE', 2205)
        uses_limit = Column(Integer, 'TICKET_USES_LIMIT', 2206)
        uses_count = Column(Integer, 'TICKET_USES_COUNT', 2207)
        expiry_ts = Column(String, 'TICKET_EXPIRY_TS', 2208)
        write_file_count = Column(Integer, 'TICKET_WRITE_FILE_COUNT', 2211)
        write_file_limit = Column(Integer, 'TICKET_WRITE_FILE_LIMIT', 2212)
        write_byte_count = Column(Integer, 'TICKET_WRITE_BYTE_COUNT', 2213)
        write_byte_limit = Column(Integer, 'TICKET_WRITE_BYTE_LIMIT', 2214)
## For now, use of these columns raises CAT_SQL_ERR in both PRC and iquest: (irods/irods#5929)
#       create_time = Column(String, 'TICKET_CREATE_TIME', 2209)
#       modify_time = Column(String, 'TICKET_MODIFY_TIME', 2210)

    class DataObject(Model):
        """For queries of R_DATA_MAIN when joining to R_TICKET_MAIN.

        The ticket(s) in question should be for a data object; otherwise
        CAT_SQL_ERR is thrown.

        """
        name = Column(String, 'TICKET_DATA_NAME', 2226)
        coll = Column(String, 'TICKET_DATA_COLL_NAME', 2227)

    class Collection(Model):
        """For queries of R_COLL_MAIN when joining to R_TICKET_MAIN.

        The returned ticket(s) will be limited to those issued for collections.

        """
        name = Column(String, 'TICKET_COLL_NAME', 2228)

    class Owner(Model):
        """For queries concerning R_TICKET_USER_MAIN."""
        name = Column(String, 'TICKET_OWNER_NAME', 2229)
        zone = Column(String, 'TICKET_OWNER_ZONE', 2230)

    class AllowedHosts(Model):
        """For queries concerning R_TICKET_ALLOWED_HOSTS."""
        ticket_id = Column(String, 'COL_TICKET_ALLOWED_HOST_TICKET_ID', 2220)
        host = Column(String, 'COL_TICKET_ALLOWED_HOST', 2221)

    class AllowedUsers(Model):
        """For queries concerning R_TICKET_ALLOWED_USERS."""
        ticket_id = Column(String, 'COL_TICKET_ALLOWED_USER_TICKET_ID', 2222)
        user_name = Column(String, 'COL_TICKET_ALLOWED_USER', 2223)

    class AllowedGroups(Model):
        """For queries concerning R_TICKET_ALLOWED_GROUPS."""
        ticket_id = Column(String, 'COL_TICKET_ALLOWED_GROUP_TICKET_ID', 2224)
        group_name = Column(String, 'COL_TICKET_ALLOWED_GROUP', 2225)
