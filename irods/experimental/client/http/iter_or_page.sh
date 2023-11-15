#!/bin/bash

if [ $# -gt 0 ]; then
  arg=${1:=iter}
else
  echo >&2 "usage: $0 [page|iter]"; exit 1
fi

python -c "
import pprint
from irods.experimental.client.http import *
s = Session('rods','rods')
i = s.genquery1('COLL_NAME', condition='',  args=(), extra_query_options=dict(count=3))
import sys
if sys.argv[1] == 'page':
    while True:
        print('---')
        p = i.next_page()
        if not p:
            break
        pprint.pprint(p)
elif sys.argv[1] == 'iter':
    for j in i:
        print('---')
        pprint.pprint(j)
        " ${arg}
