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
Useful functions to use with SacIO objects.
"""

__copyright__ = """
Copyright (c) 2012 Simon Lloyd
"""

def sac2xy(name, retarray=False):
    """
    Return time and amplitude from a SacIO object.

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param retarray:
        * True: return numpy array
        * False: return list (default)
    :type retarray: bool
    :returns: Time and amplitude of a SacIO object.
    :rtype: numpy.array or list

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> time, vals = sacfunc.sac2xy(sacobj, retarray=True)
    """
    import numpy as np
    data = name.data
    b = name.b
    delta = name.delta
    npts = name.npts
    e = b + (npts-1)*delta
    t = np.linspace(b, e, npts)
    if retarray:
        return t, np.array(data)
    return t.tolist(), data


def plotsac(name, outfile=None, showfig=True):
    """
    Simple plot of a single sac file.

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param outfile: If specified, save figure to this file.
    :type outfile: string
    :param showfig: Specifies if figure should be displayed.
    :type outfile: bool

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> sacfunc.plotsac(sacobj)
    """

    import matplotlib.pyplot as plt
    t, data = sac2xy(name)
    plt.plot(t, data)
    plt.xlabel('Time[s]')
    if outfile is not None:
        plt.savefig(outfile)
    if showfig:
        plt.show()


def resample(name, delta_new):
    """
    Resample SacIO object data using Fourier method.

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param delta_new: New sampling rate.
    :type new_delta: float
    :returns: Resampled data.
    :rtype: numpy.array

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> delta_old = sacobj.delta
        >>> delta_new = delta_old * 2
        >>> data_new = sacfunc.resample(sac, delta_new)
    """
    import scipy.signal
    data_old = name.data
    npts_old = name.npts
    delta_old = name.delta
    npts_new = int(npts_old * delta_old / delta_new)
    data_new = scipy.signal.resample(data_old, npts_new)
    return data_new


def detrend(name):
    """
    Remove linear and/or constant trends from SacIO object data.

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :returns: Detrended data.
    :rtype: numpy.array

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> detrended_data = sacfunc.detrend(sacobj)
    """

    import scipy.signal
    return scipy.signal.detrend(name.data)


def calc_az(name, ellps='WGS84'):
    """
    Calculate azimuth (in DEG) from a SacIO object. The default
    ellipse used is 'WGS84', but others may be specified. For
    more information see:

    http://trac.osgeo.org/proj/
    http://code.google.com/p/pyproj/

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param ellps: Ellipsoid to use for azimuth calculation
    :type ellps: string
    :returns: Azimuth
    :rtype: float

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> azimuth = sacfunc.calc_az(sacobj) # Use default WGS84.
        >>> azimuth = sacfunc.calc_az(sacobj, ellps='clrk66') # Use Clarke 1966 ellipsoid.
    """
    return __azdist(name, ellps)[0]


def calc_baz(name, ellps='WGS84'):
    """
    Calculate backazimuth (in DEG) from a SacIO object. The default
    ellipse used is 'WGS84', but others may be specified. For
    more information see:

    http://trac.osgeo.org/proj/
    http://code.google.com/p/pyproj/

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param ellps: Ellipsoid to use for backazimuth calculation
    :type ellps: string
    :returns: Backazimuth
    :rtype: float

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> backazimuth = sacfunc.calc_baz(sacobj) # Use default WGS84.
        >>> backazimuth = sacfunc.calc_baz(sacobj, ellps='clrk66') # Use Clarke 1966 ellipsoid.
    """
    return __azdist(name, ellps)[1]


def calc_dist(name, ellps='WGS84'):
    """
    Calculate the great circle distance (in km) from a SacIO object. The default
    ellipse used is 'WGS84', but others may be specified. For more information see:

    http://trac.osgeo.org/proj/
    http://code.google.com/p/pyproj/

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param ellps: Ellipsoid to use for distance calculation
    :type ellps: string
    :returns: Great Circle Distance
    :rtype: float

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> distance = sacfunc.calc_dist(sacobj) # Use default WGS84.
        >>> distance = sacfunc.calc_dist(sacobj, ellps='clrk66') # Use Clarke 1966 ellipsoid.
    """
    return __azdist(name, ellps)[2]


def __azdist(name, ellps):
    """
    Return forward/backazimuth and distance using
    pyproj (proj4 bindings)
    """
    from pyproj import Geod
    g = Geod(ellps=ellps)
    stla, stlo = name.stla, name.stlo
    evla, evlo = name.evla, name.evlo
    az, baz, dist = g.inv(evlo, evla, stlo, stla)
    # convert units so that they show the same as SAC
    if az < 0:
        az += 360
    if baz < 0:
        baz += 360
    dist /= 1000
    return az, baz, dist


def envelope(name, Tn, alpha):
    """
    Calculate the envelope of a gaussian filtered seismogram.

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param Tn: Center period of Gaussian filter [in seconds]
    :type Tn: float
    :param alpha: Set alpha (which determines filterwidth)
    :type alpha: float
    :returns: numpy array containing the envelope

    Example::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> envelope = sacfunc.envelope(sacobj, Tn, alpha)
    """
    return __gauss(name, Tn, alpha)[0]


def gauss(name, Tn, alpha):
    """
    Return data vector of a gaussian filtered seismogram.

    :param name: Name of the SacIO object passed to this function.
    :type name: SacIO
    :param Tn: Center period of Gaussian filter [in seconds]
    :type Tn: float
    :param alpha: Set alpha (which determines filterwidth)
    :type alpha: float
    :returns: numpy array containing filtered data

    Example usage::

        >>> from pysmo import SacIO, sacfunc
        >>> sacobj = SacIO.from_file('sacfile.sac')
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> data = sacfunc.gauss(sacobj, Tn, alpha)
    """
    return __gauss(name, Tn, alpha)[1]


def __gauss(sacobj, Tn, alpha):
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
