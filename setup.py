from setuptools import setup, find_packages


setup(name='python-irodsclient',
      version='0.5.0',
      author='iRODS Consortium',
      author_email='support@irods.org',
      description='A python API for iRODS',
      url='https://github.com/irods/python-irodsclient',
      packages=find_packages(),
      install_requires=['PrettyTable>=0.7.2'])
