#!/usr/bin/env python

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='pysmo',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    description='Python module to read/write/manipulate SAC (Seismic Analysis Code) files',
    author='Simon Lloyd',
    author_email='smlloyd@gmail.com',
    license='GNU General Public License v3.0',
    packages=find_packages(where='.', exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    data_files = [('pysmo/core/sac', ['pysmo/core/sac/sacheader.yml'])],
    zip_safe=False,
    url='https://github.com/pysmo/pysmo',
    install_requires=[
        'numpy',
        'scipy',
        'pyyaml',
        'pyproj',
        'matplotlib',
        'future'
    ],
)
