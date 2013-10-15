from distutils.core import setup
setup(
    name='python-irodsclient',
    version='0.1',
    author='Chris LaRose',
    author_email='cjlarose@iplantcollaborative.org',
    packages=['irods', 'irods.message', 'irods.resource_manager'],
    install_requires=[
        'PrettyTable>=0.7,<1.0'
    ]
)
