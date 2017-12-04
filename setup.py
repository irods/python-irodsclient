from setuptools import setup, find_packages
import os


# Get package version
version = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'irods/version.py')) as f:
    exec(f.read(), version)


setup(name='python-irodsclient',
      version=version['__version__'],
      author='iRODS Consortium',
      author_email='support@irods.org',
      description='A python API for iRODS',
      license='BSD',
      url='https://github.com/irods/python-irodsclient',
      keywords='irods',
      long_description='README.rst',
      classifiers=[
                   'License :: OSI Approved :: BSD License',
                   'Development Status :: 4 - Beta',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Python :: 3.5',
                   'Programming Language :: Python :: 3.6',
                   'Operating System :: POSIX :: Linux',
                   ],
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
                        'six>=1.10.0',
                        'PrettyTable>=0.7.2',
                        'xmlrunner>=1.7.7'
                        ]
      )
