#!/bin/bash

IRODS_HOME=/var/lib/irods
DEV_HOME="$HOME"
: ${DEV_REPOS:="$DEV_HOME/github"}

add_package_repo()
{
      local R="/etc/apt/sources.list.d/renci-irods.list"
      echo >&2 "... installing package repo"
      sudo apt update
      sudo apt install -y lsb-release apt-transport-https
      wget -qO - https://packages.irods.org/irods-signing-key.asc | sudo apt-key add - && \
      echo "deb [arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" |\
          sudo tee "$R"
      sudo apt update
}

DIST_NAME=$(lsb_release -sc)

: ${IRODS_VSN:=4.3.1-0~$DIST_NAME}

while [[ "$1" = -* ]]; do
  ARG="$1"
  shift
  case $ARG in
    --i=* | --irods=* |\
    --irods-version=*) IRODS_PACKAGE_VERSION=${ARG#*=};;
    --w=* | --with=* | --with-options=* ) withopts=${ARG#*=} ;;
    -v) VERBOSE=1;;
  esac
done


run_phase() {

 local PHASE=$1
 local with_opts=" $2 "

 case "$PHASE" in

 0)

    if [[ $with_opts = *\ initialize\ * ]]; then
        apt-get -y update
        apt-get  install -y apt-transport-https wget lsb-release sudo jq
    fi

    if [[ $with_opts = *\ sudo-without-pw\ * ]]; then
      if [ `id -u` = 0 -a "${USER:-root}" = root ] ; then
        echo >&2 "root authorization for 'sudo' is automatic - no /etc/sudoers modification needed"
      else
        if [ -f "/etc/sudoers" ]; then
           if [ -n "$USER" ] ; then
             # add a line with our USER name to /etc/sudoers if not already there
             sudo su -c "sed -n '/^\s*[^#]/p' /etc/sudoers | grep '^$USER\s*ALL=(ALL)\s*NOPASSWD:\s*ALL\s*$' >/dev/null" || \
             sudo su -c "echo '$USER ALL=(ALL) NOPASSWD: ALL' >>/etc/sudoers"
           else
             echo >&2 "user login is '$USER' - can this be right?"
           fi
        else
           echo >&2 "WARNING - Could not modify sudoers files"
           echo -n >&2 "           (hit 'Enter' to continue)"
           read key
        fi
      fi # not root
    fi # with-opts

    #------ (needed for both package install and build from source)

    if [[ $with_opts = *\ install-essential-packages\ * ]]; then

        if ! dpkg -l tzdata >/dev/null 2>&1 ; then
          sudo su - root -c \
           "env DEBIAN_FRONTEND=noninteractive bash -c 'apt-get install -y tzdata'"
        fi
        sudo apt-get update
        sudo apt-get install -y software-properties-common postgresql
        sudo apt-get update && \
        sudo apt-get install -y libfuse2 unixodbc rsyslog ################### less python-pip 
    fi


    if [[ $with_opts = *\ add-package-repo\ * ]]; then
            add_package_repo -f
    fi


    if [[ $with_opts = *\ create-db\ * ]]; then
    sudo su - postgres -c "
        { dropdb --if-exists ICAT
          dropuser --if-exists irods ; } >/dev/null 2>&1"
    sudo su - postgres -c "psql <<\\
________
        CREATE DATABASE \"ICAT\";
        CREATE USER irods WITH PASSWORD 'testpassword';
        GRANT ALL PRIVILEGES ON DATABASE \"ICAT\" to irods;
________"
    echo >&2 "-- status of create-db =  $? -- "
    fi
    ;;

 4)
   sudo apt install -y irods-{dev,runtime}${IRODS_PACKAGE_VERSION:+"=$IRODS_PACKAGE_VERSION"}
   if [[ $with_opts != *\ basic\ * ]]; then
     sudo apt install -y irods-{icommands,server,database-plugin-postgres}${IRODS_PACKAGE_VERSION:+"=$IRODS_PACKAGE_VERSION"}
   fi
 ;;

 5)
 if [ ! "$IRODS_VSN" '<' "4.3" ]; then
    PYTHON=python3
 else
    PYTHON=python2
 fi
 sudo $PYTHON /var/lib/irods/scripts/setup_irods.py < /var/lib/irods/packaging/localhost_setup_postgres.input
 ;;

 *) echo >&2 "unrecognized phase: '$PHASE'." ; QUIT=1 ;;
 esac
 return $?
}

#-------------------------- main

QUIT=0
while [ $# -gt 0 ] ; do
  ARG=$1 ; shift
  NOP="" ; run_phase $ARG " $withopts "; sts=$?
  [ $QUIT != 0 ] && break
  [ -n "$NOP" ] && continue
  echo -n "== $ARG == "
  if [ $sts -eq 0 ]; then
    echo Y >&2
  else
    [ $quit_on_phase_err ] && { echo >&2 "N - quitting"; exit 1; }
    echo N >&2
  fi
done
