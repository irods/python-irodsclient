===================
Virtualenv problems
===================

Python2 virtual environments seem broken for some older Linux
distributions, such as Ubuntu 16 and Centos 7.

However, using the system Python2 and PIP packages, the
Python iRODS Client (PRC) package can still be
installed in the system global python environment or (more
safely perhaps) in a user environment.

As an example, a non-root user such as the irods Unix user
can use the following commands to install the PRC "locally,"
meaning that the ~/.local directory will be used as the
install prefix:

  $ pip install --user --upgrade pip==20.3.1

  $ ~/.local/bin/pip install python-irodsclient

Optionally, using a local git repository, the PRC can also be
installed by replacing the latter command with:

  $ ~/.local/bin/pip install /path/to/python-irodsclient

If desired, the optional -e (or --editable) switch allows the
installed package to track changes within the repo directory.
This is most useful for experimentation, iteration, and
testing.
