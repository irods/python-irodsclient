from ssl-and-pam
run apt update
run apt install -y wget build-essential
run apt install -y libssl-dev zlib1g-dev libffi-dev libncurses-dev wget build-essential
arg python_version
run wget https://www.python.org/ftp/python/${python_version}/Python-${python_version}.tar.xz
run tar xf Python-${python_version}.tar.xz
workdir /Python-${python_version}
run ./configure --prefix /root/python --with-ensurepip=install
run make -j
run mkdir /root/python
run make install
workdir /
run /root/python/bin/python3 -m pip install python-irodsclient
run chmod a+rx /root
