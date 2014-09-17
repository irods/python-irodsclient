from setuptools import setup, find_packages


setup(name='python-irodsclient',
      version='0.3.1',
      author='iPlant Collaborative',
      author_email='atmodevs@gmail.com',
      description='A python API for iRODS',
      url='https://github.com/iPlantCollaborativeOpenSource/',
      packages=find_packages(),
      install_requires=['PrettyTable>=0.7.2'])
