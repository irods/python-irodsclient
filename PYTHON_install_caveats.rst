==================================================
Python, pip, virtualenv - caveats for use with PRC
==================================================

The Python iRODS Client (PRC) can be installed by a
non-administrative user, either locally for the user
(under ~/.local) or in a virtual environment.

If the system administrator has installed system packages
for Python and pip, and we are working on a recent
enough operating system, this is usually straightforward.
However, older distributions of the Linux OS may present
problems to installers of PRC and other PyPI packages,
particularly when the system pip and virtualenv modules
are out-of-date.

When working as a non-root user, we can best correct
this by first upgrading pip (at the time of writing,
a known working version is 20.3.4):

  $ pip install --upgrade --user pip==20.3.4

This manages the upgrade for the currently logged-in
account only, and does so by storing the upgraded pip
under the ~/.local directory.


User-local Install of PRC
-------------------------

It is now possible to set up PRC and its dependencies
for the current user, even without the use of a virtual
environment:

  $ python -m pip install --user python_irodsclient


Virtual Environment
-------------------

If the aim is to set up our project within a virtual
environment, including possibly PRC and a wider set of
packages and dependencies, best practice dictates that
we now install the latest the 'virtualenv' module:

  $ python -m pip install --user virtualenv

Then we create the virtual environment with:

  $ python -m virtualenv ~/venv

or optionally (to force a specific version of python):

  $ python -m virtualenv -p /usr/bin/python3 ~/venv

Done this way, resulting virtual environment should be
able to accommodate even the most recent PyPI packages as
appropriate for the given version of Python.

We then activate it with this command :

  $ source ~/venv/bin/activate
  
and proceed to install the desired package(s):

  (venv) $ python -m pip install <PyPI_name_or_path> ...

In that last `pip install` line, the final argument(s) can be
either PyPI package names (eg "python-irodsclient") or
a directory in the local filesystem.  In the latter case,
the command is best issued with the path argument of "."
while the current working directory is set to the location
of "setup.py".  An example would be the git repository
resulting from:

  $ git clone http://github.com/irods/python-irodsclient

