import pprint

from irods.experimental.client.http import *
from irods.experimental.client.http.iterator_functions import *

s = Session('rods','rods',host='prec3431')
c = CollManager(s).get("/tempZone/home/rods")

print ("Got a collection {c.name}, id = {c.id}".format(**locals()))

# Query collections by explicit column list.
result = s.genquery1(['COLL_ID', 'COLL_NAME'], # columns
                     "COLL_NAME like '%'",     # condition
                     extra_query_options=dict(count='512'))
print("Result of collection query:\n"
      "---------------------------\n")

result = list(result)
pprint.pprint(result)
print('Length of result was:',len(result))

# For a query of all data objects (note lack of condition argument), list full paths.
for row in s.genquery1('COLL_NAME,DATA_NAME',
                       extra_query_options=dict(count='512')):
    print('path = {COLL_NAME}/{DATA_NAME}'.format(**row._asdict()))

# Fetch the data object requested.
data_path = "/tempZone/home/alice/new_alice.dat"

print ('-- fetch first replica --')

data_obj = first_n(s.data_object(data_path),n=1)
print(data_obj)

print ('-- fetch all replicas without paging --')

MAX_REPLICAS = 2**31-1
data_obj_replicas = list(s.data_object(data_path, query_options=dict(count=MAX_REPLICAS)))
pprint.pprint(data_obj_replicas)
