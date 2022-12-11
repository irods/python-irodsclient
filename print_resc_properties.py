from irods.resource import iRODSResource
from irods.models import Resource
import irods.test.helpers as h
import sys

s = h.make_session()

r = s.resources.get(sys.argv[1])

print('id = ',r.parent_id)
print('name = ',r.parent_name)
print('resc_hier = ',r.resc_hierarchy)
