###
# This file is part of pysmo.

# psymo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# psymo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pysmo.  If not, see <http://www.gnu.org/licenses/>.
###

"""
"""

__copyright__ = """
Copyright (c) 2013 Simon Lloyd
"""

import numpy as np
from scipy.interpolate import interp1d
from scipy.integrate import cumtrapz

NLNM = dict(dB=np.array([-168.0, -166.7, -166.7, -169.2, -163.7,
                         -148.6, -141.1, -141.1, -149.0, -163.8,
                         -166.2, -162.1, -177.5, -185.0, -187.5,
                         -187.5, -185.0, -185.0, -187.5, -184.4,
                         -151.9, -103.1]),
            T=np.array([0.10, 0.17, 0.40, 0.80, 1.24, 2.40, 4.30,
                        5.00, 6.00, 10.00, 12.00, 15.60, 21.90,
                        31.60, 45.00, 70.00, 101.00, 154.00,
                        328.00, 600.00, 10**4, 10**5]))

NHNM = dict(dB=np.array([-91.5, -97.4, -110.5, -120.0, -98.0,
                         -96.5, -101.0, -113.5, -120.0, -138.5,
                         -126.0, -80.1, -48.5]),
            T=np.array([0.10, 0.22, 0.32, 0.80, 3.80, 4.60,
                        6.30, 7.90, 15.40, 20.00, 354.80,
                        10**4, 10**5]))

def _genNoise(delta, npts, NM, velocity):
    """
    Helper function for calculating random noise from noise model NM.
    """
    delta = float(delta)
    Fnyq = 0.5/delta 
    f = interp1d(NM['T'], NM['dB'], kind='linear', bounds_error=False, fill_value=-200)
    NPTS = int(2**np.ceil(np.ceil(np.log2(npts)+1))) # make it longer than necessary so we can cut out middle bit
    freqs = np.linspace(1./NPTS/delta,Fnyq,NPTS-1)
    Pxx = f(1/freqs)
    spectrum = np.zeros(NPTS)
    spectrum[1:NPTS] = np.sqrt(10**(Pxx/10) * NPTS / delta * 2)

    # phase is randomly generated
    phase = (np.random.rand(NPTS) - 0.5) * np.pi * 2

    NewX = spectrum * (np.cos(phase) + 1j * np.sin(phase))
    acceleration = np.fft.irfft(NewX)

    start = int((NPTS-npts)/2)
    end = start + npts
    if velocity:
        velocity = cumtrapz(acceleration, dx=delta)
        velocity = velocity[start:end]
        velocity = velocity - np.mean(velocity)
        return velocity
    acceleration = acceleration[start:end]
    acceleration = acceleration - np.mean(acceleration)
    return acceleration

def genNoiseNLNM(delta, npts, velocity=False):
    """
    Generate a random signal that matches Peterson's
    new low noise model NLNM.

    :param delta: Sampling rate of generated noise
    :type delta: float
    :param npts: Number of points of generated noise
    :type npts: int
    :param velocity: Return velocity instead of acceleration.
    :type velocity: bool
    :returns: numpy array containing synthetic data

    Example usage::

        >>> import pysmo.tools.noise as noise
        >>> delta = 0.05
        >>> npts = 5000
        >>> low_noise = noise.genNoiseNLNM(delta, npts)
    """
    return _genNoise(delta, npts, NLNM, velocity)

def genNoiseNHNM(delta, npts, velocity=False):
    """
    Generate a random signal that matches Peterson's
    new high noise model NHNM.

    :param delta: Sampling rate of generated noise
    :type delta: float
    :param npts: Number of points of generated noise
    :type npts: int
    :param velocity: Return velocity instead of acceleration.
    :type velocity: bool
    :returns: numpy array containing synthetic data

    Example usage::

        >>> import pysmo.tools.noise as noise
        >>> delta = 0.05
        >>> npts = 5000
        >>> high_noise = noise.genNoiseNHNM(delta, npts)
    """
    return _genNoise(delta, npts, NHNM, velocity)
