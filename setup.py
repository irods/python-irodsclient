from setuptools import find_packages, setup
setup(
    name='python-irodsclient',
    version='0.3',
    author='Chris LaRose',
    author_email='cjlarose@iplantcollaborative.org',
    packages=find_packages(),
    install_requires=[
        'PrettyTable>=0.7,<1.0'
    ]
)
