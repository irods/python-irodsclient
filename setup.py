from distutils.core import setup
setup(
    name='pycommands',
    version='0.0',
    author='Chris LaRose',
    author_email='cjlarose@iplantcollaborative.org',
    packages=['irods', 'irods.message', 'irods.resource_manager'],
    install_requires=[
        'PrettyTable>=0.7,<1.0'
    ]
)
