from install-irods
run apt update
run apt install -y wget build-essential libssl-dev zlib1g-dev
run apt install wget build-essential
run wget https://www.python.org/ftp/python/3.12.2/Python-3.12.2.tar.xz
run tar xf Python-3.12.2.tar.xz
workdir /Python-3.12.2
run ./configure --prefix /root/python --with-ensurepip=install
run make -j
run mkdir /root/python
run make install
workdir /
run /root/python/bin/python3 -m pip install python-irodsclient
run chmod a+rx /root
