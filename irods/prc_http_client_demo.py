import pprint

from irods.client.experimental.http import *

s = Session('rods','rods',host='prec3431')
c = CollManager(s).get("/tempZone/home/rods")

print ("Got a collection {c.name}, id = {c.id}".format(**locals()))

# TODO: a *_generator or *_pager method which iterates or pages through results

# collections

result = s.genquery1(['COLL_ID', 'COLL_NAME'], # columns
                     "COLL_NAME like '%'",     # condition
                     extra_query_options=dict(count='512'))

pprint.pprint(result)
print('len=',len(result))

# data objects, list full paths

for row in s.genquery1('COLL_NAME,DATA_NAME',                         # note 1 - we can also parse the <columns> from a string
                                                                      # note 2 - <conditions> argument is optional
                       extra_query_options=dict(count='512')):
    print('path = {row.COLL_NAME}/{row.DATA_NAME}'.format(**locals()))
