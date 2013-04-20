from distutils.core import setup
setup(name='pycommands',
      version='0.0',
      author='Chris LaRose',
      author_email='cjlarose@iplantcollaborative.org',
      packages=['irods', 'irods.message'],
      requires=['prettytable==0.7.2']
      )
