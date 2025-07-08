from install-irods
run apt update; apt install -y python3-pip bats
run python3 -m pip install --upgrade pip
run python3 -m pip install virtualenv
run python3 -m virtualenv /py3
