FROM bats-python3
RUN apt install -y sudo
RUN useradd -ms/bin/bash testuser
RUN echo 'testuser ALL=(ALL) NOPASSWD: ALL' >>/etc/sudoers
