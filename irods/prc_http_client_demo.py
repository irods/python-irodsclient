import pprint

from irods.experimental.client.http import *

s = Session('rods','rods',host='prec3431')
c = CollManager(s).get("/tempZone/home/rods")

print ("Got a collection {c.name}, id = {c.id}".format(**locals()))

# TODO: a *_generator or *_pager method which iterates or pages through results

# Query collections by explicit column list.
result = s.genquery1(['COLL_ID', 'COLL_NAME'], # columns
                     "COLL_NAME like '%'",     # condition
                     extra_query_options=dict(count='512'))
print("Result of collection query:\n"
      "---------------------------\n")
pprint.pprint(result)
print('Length of result was:',len(result))

# For a query of all data objects (note lack of condition argument), list full paths.
for row in s.genquery1('COLL_NAME,DATA_NAME',
                       extra_query_options=dict(count='512')):
    print('path = {COLL_NAME}/{DATA_NAME}'.format(**row._asdict()))

# Fetch all columns for the data object requested.
data_path = "/tempZone/home/alice/new_alice.dat"
x = s.data_object_replicas(data_path)
print("'{}' has {} replicas we can access".format(data_path, len(x)))
