FROM bats-and-system-python
RUN apt update && \
    apt install -y wget build-essential && \
    apt install -y libssl-dev zlib1g-dev libffi-dev libncurses-dev wget build-essential
ARG python_version
RUN wget https://www.python.org/ftp/python/${python_version}/Python-${python_version}.tar.xz && \
    tar xf Python-${python_version}.tar.xz
WORKDIR /Python-${python_version}
RUN ./configure --prefix /root/python --with-ensurepip=install && \
    make -j && \
    mkdir /root/python && \
    make install
WORKDIR /
RUN /root/python/bin/python3 -m pip install virtualenv && \
    chmod a+rx /root
ENV PYTHON_VERSION=${python_version}
