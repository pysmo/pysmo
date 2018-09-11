"""
This module provides support for calculating random synthetic noise that matches the naturally observed amplitude spectrum.

See Also:

Peterson, J., 1993. Observations and modelling of background seismic noise.
Open-file report 93-322, U. S. Geological Survey, Albuquerque, New Mexico. 
"""

__all__ = [ 'NLNM', 'NHNM', 'genNoiseNHNM', 'genNoiseNLNM' ] 

from .peterson import *
