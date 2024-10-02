#!/bin/bash
service postgresql start
x=${DB_WAIT_SEC:-20}
while [ $x -ge 0 ] && { ! $SUDO su - postgres -c "psql -c '\l' >/dev/null 2>&1" || x=""; }
do
  [ -z "$x" ] && break
  echo >&2 "$((x--)) secs til database timeout"; sleep 1
done
[ -z "$x" ] || { echo >&2 "Error -- database didn't start" ; exit 1; }
if ! id -u irods >/dev/null 2>&1 ; then
    /install.sh --w=create-db 0
    VERSION_file=$(ls /var/lib/irods/{VERSION,version}.json.dist 2>/dev/null)
    IRODS_VSN=$(jq -r '.irods_version' $VERSION_file) /install.sh 5
fi
su - irods -c '~/irodsctl restart'
pgrep irodsServer
STATUS=$?
echo "($STATUS)" >/tmp/irods_status
[ $STATUS -eq 0 ] || exit 125
tail -f /dev/null
