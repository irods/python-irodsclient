#!/bin/bash
service postgresql start
x=${DB_WAIT_SEC:-20}
while [ $x -ge 0 ] && { ! $SUDO su - postgres -c "psql -c '\l' >/dev/null 2>&1" || x=""; }
do
  [ -z "$x" ] && break
  echo >&2 "$((x--)) secs til database timeout"; sleep 1
done
[ -z "$x" ] || { echo >&2 "Error -- database didn't start" ; exit 1; }
VERSION_file=$(ls /var/lib/irods/{VERSION,version}.json.dist 2>/dev/null)
if ! id -u irods >/dev/null 2>&1 ; then
    /install.sh --w=create-db 0
    /install.sh 5
fi
IRODS_VSN=$(jq -r '.irods_version' $VERSION_file)
IRODS_VSN_MAJOR=${IRODS_VSN//.*/}
if [ "$IRODS_VSN_MAJOR" -lt 5 ]; then
    su - irods -c '~/irodsctl restart'
else
    /manage_irods5_procs start
fi
IRODS_WAIT_SEC=20
x=$IRODS_WAIT_SEC
SLEEPTIME=""
while [ $((x--)) -gt 0 ]; do
  sleep $((SLEEPTIME+0))
  pgrep irodsServer
  STATUS=$?
  [ $STATUS -eq 0 ] && break
  SLEEPTIME=1
done
echo "($STATUS)" >/tmp/irods_status
[ $STATUS -eq 0 ] || exit 125
tail -f /dev/null
