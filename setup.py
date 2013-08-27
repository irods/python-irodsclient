from distutils.core import setup
setup(
    name='pycommands',
    version='0.0',
    author='Chris LaRose',
    author_email='cjlarose@iplantcollaborative.org',
    packages=['irods', 'irods.message'],
    install_requires=[
        'PrettyTable>=0.7,<1.0'
    ]
)
