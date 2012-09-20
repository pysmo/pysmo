#!/usr/bin/env python
from distutils.core import setup

setup(
    name='pysmo.sac',
    version='0.5',
    description='Python module to read/write/manipulate SAC (Seismic Analysis Code) files',
    author='Simon Lloyd',
    author_email='smlloyd@gmail.com',
    packages =['pysmo', 'pysmo.sac'],
    package_dir={'pysmo.sac': 'src/pysmo/sac', 'pysmo': 'src/pysmo'}
    )
