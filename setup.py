import setuptools


setuptools.setup(name='python-irodsclient',
                 version='0.3.1',
                 author='iPlant Collaborative',
                 author_email='atmodevs@gmail.com',
                 packages=['irods',
                           'irods.message',
                           'irods.resource_manager'],
                 install_requires=['PrettyTable>=0.7'])
