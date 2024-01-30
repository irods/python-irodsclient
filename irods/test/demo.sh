#!/bin/bash

echo "$0 running"
echo args:
for arg in $*; do
    echo $((++x)): "[$arg]"
done

exit 118
