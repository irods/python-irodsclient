from setuptools import setup, find_packages
try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()


setup(name='python-irodsclient',
      version='0.6.0',
      author='iRODS Consortium',
      author_email='support@irods.org',
      description='A python API for iRODS',
      license='BSD',
      url='https://github.com/irods/python-irodsclient',
      keywords='irods',
      long_description=read_md('README.md'),
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
      install_requires=['PrettyTable>=0.7.2'])
