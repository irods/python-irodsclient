from setuptools import setup, find_packages


setup(name='python-irodsclient',
      version='0.5.0rc1',
      author='iRODS Consortium',
      author_email='support@irods.org',
      description='A python API for iRODS',
      license='BSD',
      url='https://github.com/irods/python-irodsclient',
      keywords='irods',
      classifiers=[
                   'License :: OSI Approved :: BSD License',
                   'Development Status :: 2 - Pre-Alpha',
                   'Programming Language :: Python :: 2.7',
                   'Operating System :: POSIX :: Linux',
                   ],
      packages=find_packages(),
      install_requires=['PrettyTable>=0.7.2'])
