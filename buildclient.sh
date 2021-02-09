#!/bin/bash
SW_CACHE= #--no-cache 
cat > .env <<EOF
python_version=3
os_image=ubuntu:18.04
os_generic=ubuntu
irods_pkg_dir=/home/daniel/jenkins_sandbox/Ubuntu_18
EOF
docker-compose build $SW_CACHE client-runner
rm -fr .env
