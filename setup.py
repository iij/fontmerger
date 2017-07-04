#!/usr/bin/env python

from distutils.core import setup

from setuptools import find_packages

from fontmerger import VERSION

setup(name='fontmerger',
      version=VERSION,
      description='merging font tools',
      author='Internet Initiative Japan Inc',
      license='MIT',
      author_email='yosinobu@iij.ad.jp',
      url='https://github.com/iij/fontmerger',
      packages=find_packages(),
      package_dir={'fontmerger': 'fontmerger'},
      package_data={'fontmerger': ['terminal.png', 'fonts.json', 'LICENSE', 'README.md', 'fonts/*']},
      entry_points={
          'console_scripts': ['fontmerger=fontmerger:main'],
      })
