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

__copyright__ = """
Copyright (c) 2012 Simon Lloyd
"""
from pysmo import SacIO
import pysmo.sacfunc as sf


class SacIOExt(SacIO):
    """
    Inherited class to do more then basic IO on a SacFile object.
    Basically this is to provide an alternative way of using the
    funtions in sacfunc.py.
    """

    def plot_single_sac(self):
        sf.plot_single_sac(self)

    def resample(self, delta_new):
        self.data = sf.resample(self, delta_new)
        self.delta = delta_new

    def detrend(self):
        self.data = sf.detrend(self)

    def calc_az(self, ellps='WGS84'):
        try:
            self.az = sf.calc_az(self, ellps)
        except:
            pass

    def calc_baz(self, ellps='WGS84'):
        try:
            self.baz = sf.calc_baz(self, ellps)
        except:
            pass

    def calc_dist(self, ellps='WGS84'):
        try:
            self.dist = sf.calc_dist(self, ellps)
        except:
            pass
