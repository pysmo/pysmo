#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='pysmo_sac',
    version='0.5.1',
    description='Python module to read/write/manipulate SAC (Seismic Analysis Code) files',
    long_description='',
    author='Simon Lloyd',
    author_email='smlloyd@gmail.com',
    license='GNU General Public License v3.0',
    packages=find_packages(where='.'),
    zip_safe=False,
)
