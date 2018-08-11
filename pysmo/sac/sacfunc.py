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
Python module for manipulating SAC file objects.

Public functions:
 - plot_single_sac(sacobj)          create and show simple plot of one trace
 - resample(sacobj, delta_new)      resample data
 - detrend(sacobj)                  detrend
 - calc_az(sacobj, ellps='WGS84')   azimuth
 - calc_baz(sacobj, ellps='WGS84')  backazimuth
 - calc_dist(sacobj, ellps='WGS84') great circle distance
 - envelope(sacobj, Tn, alpha)      return data vector of the envelope of gaussian shaped filtered
 - gauss(sacobj, Tn, alpha)         return data vector of gaussian filtered seismogram
"""

__copyright__ = """
Copyright (c) 2012 Simon Lloyd
"""

def sac2xy(sacobj, retarray=False):
    """
    Return time and amplitude from a sacfile.

    Default is to return a python list. With
    kwarg retarray=True a numpy array is returned

    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac')
    >>> time, vals = sacfunc.sac2xy(sacobj, retarray=True)
    """
    import numpy as np
    data = sacobj.data
    b = sacobj.b
    delta = sacobj.delta
    npts = sacobj.npts
    e = b + (npts-1)*delta
    t = np.linspace(b, e, npts)
    if retarray:
        return t, np.array(data)
    return t.tolist(), data

def plotsac(sacobj, outfile=None, showfig=True):
    """
    Simple plot of a single sac file.

    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac')
    >>> sacfunc.plotsac(sacobj)
    """
    import matplotlib.pyplot as plt
    t, data = sac2xy(sacobj)
    fig = plt.figure()
    plt.plot(t, data)
    plt.xlabel('Time[s]')
    if outfile is not None:
        plt.savefig(outfile)
    if showfig:
        plt.show()

def resample(sacobj, delta_new):
    """
    Resample the data using Fourier method.

    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac', 'rw')
    >>> delta_old = sacobj.delta
    >>> delta_new = delta_old * 2
    >>> data_new = sacfunc.resample(sac, delta_new)
    """
    import scipy.signal
    data_old = sacobj.data
    npts_old = sacobj.npts
    delta_old = sacobj.delta
    npts_new = int(npts_old * delta_old / delta_new)
    data_new = scipy.signal.resample(data_old, npts_new)
    return data_new

def detrend(sacobj):
    """
    Remove linear and/or constant trends from data.

    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac', 'rw')
    >>> detrended_data = sacfunc.detrend(sacobj)
    """
    import scipy.signal
    return scipy.signal.detrend(sacobj.data)

def calc_az(sacobj, ellps='WGS84'):
    """
    Return azimuth (in DEG) from sacfile. The default
    ellipse used is 'WGS84', but others may be specified. For
    more information see:

    http://trac.osgeo.org/proj/
    http://code.google.com/p/pyproj/

    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac')
    >>> azimuth = sacfunc.calc_az(sacobj) # Use default WGS84.
    >>> azimuth = sacfunc.calc_az(sacobj, ellps='clrk66') # Use Clarke 1966 ellipsoid.
    """
    return __azdist(sacobj, ellps)[0]

def calc_baz(sacobj, ellps='WGS84'):
    """
    Return backazimuth (in DEG) from sacfile. The default
    ellipse used is 'WGS84', but others may be specified. For
    more information see:

    http://trac.osgeo.org/proj/
    http://code.google.com/p/pyproj/

    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac')
    >>> backazimuth = sacfunc.calc_baz(sacobj) # Use default WGS84.
    >>> backazimuth = sacfunc.calc_baz(sacobj, ellps='clrk66') # Use Clarke 1966 ellipsoid.
    """
    return __azdist(sacobj, ellps)[1]

def calc_dist(sacobj, ellps='WGS84'):
    """
    Return great circle distance (in km) from sacfile. The default
    ellipse used is 'WGS84', but others may be specified. For
    more information see:

    http://trac.osgeo.org/proj/
    http://code.google.com/p/pyproj/

    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = pysmo.sac.sacio.sacfile('file.sac')
    >>> distance = sacfunc.calc_dist(sacobj) # Use default WGS84.
    >>> distance = sacfunc.calc_dist(sacobj, ellps='clrk66') # Use Clarke 1966 ellipsoid.
    """
    return __azdist(sacobj, ellps)[2]

def __azdist(sacobj, ellps):
    """
    Return forward/backazimuth and distance using
    pyproj (proj4 bindings)
    """
    from pyproj import Geod
    g = Geod(ellps=ellps)
    stla, stlo = sacobj.stla, sacobj.stlo
    evla, evlo = sacobj.evla, sacobj.evlo
    az, baz, dist = g.inv(evlo, evla, stlo, stla)
    # convert units so that they show the same as SAC
    if az < 0:
        az += 360
    if baz < 0:
        baz += 360
    dist /= 1000
    return az, baz, dist

def envelope(sacobj, Tn, alpha):
    """
    Return data vector of the envelope of gaussian filtered seismogram.
    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac')
    >>> Tn = 50 # Center Gaussian filter at 50s period
    >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
    >>> envelope = sacfunc.envelope(sacobj, Tn, alpha)
    """
    return __gauss(sacobj, Tn, alpha)[0]

def gauss(sacobj, Tn, alpha):
    """
    Return data vector of a gaussian filtered seismogram.
    Example:
    >>> import pysmo.sac.sacio as sacio
    >>> import pysmo.sac.sacfunc as sacfunc
    >>> sacobj = sacio.sacfile('file.sac')
    >>> Tn = 50 # Center Gaussian filter at 50s period
    >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
    >>> data = sacfunc.gauss(sacobj, Tn, alpha)
    """
    return __gauss(sacobj, Tn, alpha)[1]

def __gauss(sacobj, Tn, alpha):
    """
    Return envelope and gaussian filtered data
    """
    import numpy as np
    data = np.array(sacobj.data)
    delta = sacobj.delta
    Wn = 1 / float(Tn)
    Nyq = 1 / (2 * delta)
    old_size = data.size
    pad_size = 2**(int(np.log2(old_size))+1)
    data.resize(pad_size)
    spec = np.fft.fft(data)
    spec.resize(pad_size)
    W = np.array(np.linspace(0, Nyq, pad_size))
    Hn = spec * np.exp(-1 * alpha * ((W-Wn)/Wn)**2)
    Qn = complex(0, 1) * Hn.real - Hn.imag
    hn = np.fft.ifft(Hn).real
    qn = np.fft.ifft(Qn).real
    an = np.sqrt(hn**2 + qn**2)
    an.resize(old_size)
    hn = hn[0:old_size]
    return(an, hn)
