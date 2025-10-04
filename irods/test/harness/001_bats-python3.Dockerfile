FROM install-irods
RUN apt update; apt install -y python3-pip bats
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install virtualenv
RUN python3 -m virtualenv /py3
