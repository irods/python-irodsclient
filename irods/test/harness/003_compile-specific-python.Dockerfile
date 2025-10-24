FROM ssl-and-pam
RUN apt update
RUN apt install -y wget build-essential
RUN apt install -y libssl-dev zlib1g-dev libffi-dev libncurses-dev wget build-essential
ARG python_version
RUN wget https://www.python.org/ftp/python/${python_version}/Python-${python_version}.tar.xz
RUN tar xf Python-${python_version}.tar.xz
WORKDIR /Python-${python_version}
RUN ./configure --prefix /root/python --with-ensurepip=install
RUN make -j
RUN mkdir /root/python
RUN make install
WORKDIR /
RUN /root/python/bin/python3 -m pip install virtualenv
RUN chmod a+rx /root
ENV PYTHON_VERSION=${python_version}
