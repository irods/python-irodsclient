ARG os_version="ubuntu:20.04"
FROM ${os_version}
COPY install.sh /
ARG irods_package_version
ENV IRODS_PACKAGE_VERSION "$irods_package_version"
RUN for phase in initialize install-essential-packages add-package-repo; do \
        bash /install.sh --w=$phase 0; \
    done
RUN /install.sh 4
COPY start_postgresql_and_irods.sh /
RUN apt install -y sudo
RUN useradd -ms/bin/bash testuser
RUN echo 'testuser ALL=(ALL) NOPASSWD: ALL' >>/etc/sudoers
RUN apt install -y faketime
CMD bash /start_postgresql_and_irods.sh
