from setuptools import setup, find_packages
import codecs
import os


# Get package version
version = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "irods/version.py")) as file:
    exec(file.read(), version)


# Get description
with codecs.open("README.md", "r", "utf-8") as file:
    long_description = file.read()


setup(
    name="python-irodsclient",
    version=version["__version__"],
    author="iRODS Consortium",
    author_email="support@irods.org",
    description="A python API for iRODS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="BSD",
    url="https://github.com/irods/python-irodsclient",
    keywords="irods",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: POSIX :: Linux",
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PrettyTable>=0.7.2",
        "defusedxml",
        "jsonpointer",
        "jsonpatch",
    ],
    extras_require={"tests": ["unittest-xml-reporting",  # for xmlrunner
                              "types-defusedxml",        # for type checking
                              "progressbar",             # for type checking
                              "types-tqdm"]              # for type checking
                   },
    scripts=["irods/prc_write_irodsA.py"],
)
