#!/bin/bash
usage() {
    echo >&2 "Usage:
    $0 major.minor"
    echo >&2 "Output:
    prints full latest python version inclusive of the patch level."
    exit 2
}
MAJOR_MINOR=$1
if [ -z "${MAJOR_MINOR}" ]; then # allow blank specification: most recent overall
    MAJOR_MINOR='[0-9]\+\.[0-9]\+'
elif [[ $MAJOR_MINOR =~ ^[0-9]+$ ]]; then # allow single integer, eg. 3 for most recent 3.y.z
    MAJOR_MINOR+='\.[0-9]\+'
elif [[ $MAJOR_MINOR =~ [0-9]+\.[0-9]+ ]]; then        # allow x.y form, will yield output of most recent x.y.z
    MAJOR_MINOR=$(sed 's/\./\\./' <<<"${MAJOR_MINOR}") # insert backslash in front of "."
elif ! [[ $MAJOR_MINOR =~ [0-9]+\\?.[0-9]+ ]]; then
    usage
fi

url='https://www.python.org/ftp/python/'

# Fetch the directory listing, extract version numbers, sort them to find the largest numerically.
curl --silent "$url" |
    sed -n 's!.*href="\('"${MAJOR_MINOR}"'\.[0-9]\+\)/".*!\1!p' | sort -rV |
    head -n 1
