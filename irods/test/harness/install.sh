#!/bin/bash

# A script to manage the main steps in installing an iRODS server as well as all necessary support. (Dependencies,
# catalog database, etc.)

IRODS_HOME=/var/lib/irods
DEV_HOME="$HOME"
: ${DEV_REPOS:="$DEV_HOME/github"}

add_package_repo()
{
      echo >&2 "... installing package repo"
      sudo apt update
      sudo apt install -y lsb-release apt-transport-https gnupg2
      wget -qO - https://packages.irods.org/irods-signing-key.asc | \
          gpg \
              --no-options \
              --no-default-keyring \
              --no-auto-check-trustdb \
              --homedir /dev/null \
              --no-keyring \
              --import-options import-export \
              --output /etc/apt/keyrings/renci-irods-archive-keyring.pgp \
              --import \
          && \
      echo "deb [signed-by=/etc/apt/keyrings/renci-irods-archive-keyring.pgp arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" | \
          tee /etc/apt/sources.list.d/renci-irods.list

      sudo apt update
}

# Expand a spec of the leading version tuple eg. 4.3.4 out  to the full name of
# the most recent matching version of the package

# Report the latest version spec (including OS) that matches the env var IRODS_PACKAGE_VERSION (eg. "5.0.2" -> "5.0.2-0~jammy)

irods_package_vsn() {
  apt list -a irods-server 2>/dev/null|awk '{print $2}'|grep '\w'|sort|\
      grep "$(perl -e 'print quotemeta($ARGV[0])' "$IRODS_PACKAGE_VERSION")"|tail -1
}

# Report the version number of the installed iRODS server if any.

irods_vsn() {
  local V=$(dpkg -l irods-server 2>/dev/null|grep '^ii\s'|awk '{print $3}')
  echo "${V}"
}

while [[ "$1" = -* ]]; do
  ARG="$1"
  shift
  case $ARG in
    --i=* | --irods=* |\
    --irods-version=*) IRODS_PACKAGE_VERSION=${ARG#*=};;
    --w=* | --with=* | --with-options=* ) withopts=${ARG#*=} ;;
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
      if [ $(id -u) = 0 -a "${USER:-root}" = root ] ; then
        echo >&2 "root authorization for 'sudo' is automatic - no /etc/sudoers modification needed"
      else
        if [ -f "/etc/sudoers" ]; then
            # add a line with our USER name to /etc/sudoers if not already there
            sudo su -c "sed -n '/^\s*[^#]/p' /etc/sudoers | grep '^$USER\s*ALL=(ALL)\s*NOPASSWD:\s*ALL\s*$' >/dev/null" || \
            sudo su -c "echo '$USER ALL=(ALL) NOPASSWD: ALL' >>/etc/sudoers"
        else
            echo >&2 "WARNING - Could not modify sudoers files"
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
        sudo apt-get install -y libfuse2 unixodbc rsyslog
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
   IRODS_TO_INSTALL=$(irods_package_vsn)
   sudo apt install -y irods-{dev,runtime}${IRODS_TO_INSTALL:+"=$IRODS_TO_INSTALL"}
   if [[ $with_opts != *\ basic\ * ]]; then
     sudo apt install -y irods-{icommands,server,database-plugin-postgres}${IRODS_TO_INSTALL:+"=$IRODS_TO_INSTALL"}
   fi
 ;;

 5)
 if [ ! $(irods_vsn) '<' "4.3" ]; then
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
