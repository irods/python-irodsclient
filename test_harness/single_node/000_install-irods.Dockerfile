FROM ubuntu:22.04
COPY install.sh /
ARG irods_package_version
ENV IRODS_PACKAGE_VERSION="$irods_package_version"
RUN for phase in initialize install-essential-packages add-package-repo; do \
        bash /install.sh --w=$phase 0; \
    done && \
    /install.sh 4
COPY start_postgresql_and_irods.sh manage_irods5_procs /
RUN apt install -y sudo && \
    useradd -ms/bin/bash testuser && \
    echo 'testuser ALL=(ALL) NOPASSWD: ALL' >>/etc/sudoers
ENV IRODS_CONTROL_PATH=""
CMD bash $IRODS_CONTROL_PATH/start_postgresql_and_irods.sh
