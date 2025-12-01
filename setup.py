import os

from setuptools import setup

# Get package version
version = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "irods/version.py")) as file:
    exec(file.read(), version)

setup(
    version=version["__version__"],
)
