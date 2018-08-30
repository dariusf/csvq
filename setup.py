import os
from codecs import open

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'readme.md'), encoding='utf-8') as f:
  long_description = f.read()

setup(
  name='csvq',
  version='0.0.1',
  description='Query CSV files with SQL',
  long_description=long_description,
  url='http://github.com/dariusf/csvq',
  author='Darius Foo',
  author_email='darius.foo.tw@gmail.com',
  license='MIT',
  packages=find_packages(),
  include_package_data=True,
  entry_points={
    'console_scripts': [
      'csv=csvq.cli:main',
      'csvq=csvq.cli:main'
    ]
  },
  install_requires=[
  ]
)
