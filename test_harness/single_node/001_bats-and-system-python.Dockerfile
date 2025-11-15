FROM install-irods
RUN apt update
RUN apt install -y python3-pip bats && \
    python3 -m pip install --upgrade pip && \
    python3 -m pip install virtualenv && \
    python3 -m virtualenv /py3
