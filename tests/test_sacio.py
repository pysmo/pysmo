#!/usr/bin/env python

import unittest
import os
import tempfile
import shutil
from pysmo.sac import sacio

class sacioTestCase(unittest.TestCase):
    """Tests for `sacio.py`."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        testfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
        ro_file = os.path.join(self.tmpdir, 'readonly.sac')
        rw_file = os.path.join(self.tmpdir, 'readwrite.sac')
        new_file = os.path.join(self.tmpdir, 'new.sac')
        shutil.copyfile(testfile, ro_file)
        shutil.copyfile(testfile, rw_file)
        self.ro_sacobj = sacio.sacfile(ro_file, 'ro')
        self.rw_sacobj = sacio.sacfile(rw_file, 'rw')
        self.new_sacobj = sacio.sacfile(new_file, 'new')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_read_headers(self):
        """
        Read header values in our test file and
        check if they match the expected value.
        """
        self.assertEqual(self.ro_sacobj.npts, 180000)
        self.assertAlmostEqual(self.ro_sacobj.b, 53.060001373291016)
        self.assertAlmostEqual(self.ro_sacobj.e, 3653.0400390625)
        self.assertEqual(self.ro_sacobj.iftype, 'time')
        self.assertTrue(self.ro_sacobj.leven)
        self.assertAlmostEqual(self.ro_sacobj.delta, 0.02)
        with self.assertRaises(ValueError): self.ro_sacobj.odelta
        self.assertEqual(self.ro_sacobj.idep, 'unkn')
        self.assertAlmostEqual(self.ro_sacobj.depmin, -8293.0)
        self.assertAlmostEqual(self.ro_sacobj.depmax, 3302.0)
        self.assertAlmostEqual(self.ro_sacobj.depmen, -572.200439453125)
        self.assertAlmostEqual(self.ro_sacobj.o, 0.0)
        with self.assertRaises(ValueError): self.ro_sacobj.a
        with self.assertRaises(ValueError): self.ro_sacobj.t0
        with self.assertRaises(ValueError): self.ro_sacobj.t1
        with self.assertRaises(ValueError): self.ro_sacobj.t2
        with self.assertRaises(ValueError): self.ro_sacobj.t3
        with self.assertRaises(ValueError): self.ro_sacobj.t4
        with self.assertRaises(ValueError): self.ro_sacobj.t5
        with self.assertRaises(ValueError): self.ro_sacobj.t6
        with self.assertRaises(ValueError): self.ro_sacobj.t7
        with self.assertRaises(ValueError): self.ro_sacobj.t8
        with self.assertRaises(ValueError): self.ro_sacobj.t9
        with self.assertRaises(ValueError): self.ro_sacobj.f
        # kzdate is a derived header
        # kztime is a derived header
        self.assertEqual(self.ro_sacobj.iztype, 'o')
        with self.assertRaises(ValueError): self.ro_sacobj.kinst
        with self.assertRaises(ValueError): self.ro_sacobj.resp0
        with self.assertRaises(ValueError): self.ro_sacobj.resp1
        with self.assertRaises(ValueError): self.ro_sacobj.resp2
        with self.assertRaises(ValueError): self.ro_sacobj.resp3
        with self.assertRaises(ValueError): self.ro_sacobj.resp4
        with self.assertRaises(ValueError): self.ro_sacobj.resp5
        with self.assertRaises(ValueError): self.ro_sacobj.resp6
        with self.assertRaises(ValueError): self.ro_sacobj.resp7
        with self.assertRaises(ValueError): self.ro_sacobj.resp8
        with self.assertRaises(ValueError): self.ro_sacobj.resp9
        with self.assertRaises(ValueError): self.ro_sacobj.kdatrd
        self.assertEqual(self.ro_sacobj.kstnm, 'MEL01')
        self.assertAlmostEqual(self.ro_sacobj.cmpaz, 0)
        self.assertAlmostEqual(self.ro_sacobj.cmpinc, 90)
        with self.assertRaises(ValueError): self.ro_sacobj.istreg
        self.assertAlmostEqual(self.ro_sacobj.stla, -43.855464935302734)
        self.assertAlmostEqual(self.ro_sacobj.stlo, -73.74272155761719)
        with self.assertRaises(ValueError): self.ro_sacobj.stel
        with self.assertRaises(ValueError): self.ro_sacobj.stdp
        self.assertEqual(self.ro_sacobj.kevnm, '043550359BHN')
        with self.assertRaises(ValueError): self.ro_sacobj.ievreg
        self.assertAlmostEqual(self.ro_sacobj.evla, -15.265999794006348)
        self.assertAlmostEqual(self.ro_sacobj.evlo, -75.20800018310547)
        with self.assertRaises(ValueError): self.ro_sacobj.evel
        self.assertAlmostEqual(self.ro_sacobj.evdp, 30.899999618530273)
        self.assertEqual(self.ro_sacobj.ievtyp, 'quake')
        self.assertEqual(self.ro_sacobj.khole, '')
        self.assertAlmostEqual(self.ro_sacobj.dist, 3172.399658203125)
        self.assertAlmostEqual(self.ro_sacobj.az, 177.77978515625)
        self.assertAlmostEqual(self.ro_sacobj.baz, 357.0372619628906)
        self.assertAlmostEqual(self.ro_sacobj.gcarc, 28.522098541259766)
        self.assertTrue(self.ro_sacobj.lovrok)
        with self.assertRaises(ValueError): self.ro_sacobj.iqual
        with self.assertRaises(ValueError): self.ro_sacobj.isynth
        with self.assertRaises(ValueError): self.ro_sacobj.user0
        with self.assertRaises(ValueError): self.ro_sacobj.user1
        with self.assertRaises(ValueError): self.ro_sacobj.user2
        with self.assertRaises(ValueError): self.ro_sacobj.user3
        with self.assertRaises(ValueError): self.ro_sacobj.user4
        with self.assertRaises(ValueError): self.ro_sacobj.user5
        with self.assertRaises(ValueError): self.ro_sacobj.user6
        with self.assertRaises(ValueError): self.ro_sacobj.user7
        self.assertAlmostEqual(self.ro_sacobj.user8, 4.900000095367432)
        self.assertAlmostEqual(self.ro_sacobj.user9, 5.000000)
        with self.assertRaises(ValueError): self.ro_sacobj.kuser0
        with self.assertRaises(ValueError): self.ro_sacobj.kuser1
        with self.assertRaises(ValueError): self.ro_sacobj.kuser2
        with self.assertRaises(ValueError): self.ro_sacobj.nxsize
        with self.assertRaises(ValueError): self.ro_sacobj.xminimum
        with self.assertRaises(ValueError): self.ro_sacobj.xmaximum
        with self.assertRaises(ValueError): self.ro_sacobj.nysize
        with self.assertRaises(ValueError): self.ro_sacobj.yminimum
        with self.assertRaises(ValueError): self.ro_sacobj.ymaximum
        self.assertEqual(self.ro_sacobj.nvhdr, 6)
        with self.assertRaises(ValueError): self.ro_sacobj.scale
        self.assertEqual(self.ro_sacobj.norid, 0)
        self.assertEqual(self.ro_sacobj.nevid, 0)
        self.assertEqual(self.ro_sacobj.nwfid, 13)
        with self.assertRaises(ValueError): self.ro_sacobj.iinst
        self.assertTrue(self.ro_sacobj.lpspol)
        self.assertTrue(self.ro_sacobj.lcalda)
        self.assertEqual(self.ro_sacobj.kcmpnm, 'BHN')
        self.assertEqual(self.ro_sacobj.knetwk, 'YJ')
        with self.assertRaises(ValueError): self.ro_sacobj.mag
        with self.assertRaises(ValueError): self.ro_sacobj.imagtyp
        with self.assertRaises(ValueError): self.ro_sacobj.imagsrc

        # try reading illegal header
        with self.assertRaises(AttributeError): self.ro_sacobj.nonexistingheader

    def test_write_headers(self):
        """
        Test changing header values
        """

        # readonly sacfile object should raise an error
        with self.assertRaises(IOError):
            self.ro_sacobj.delta = 2

        delta = 0.123
        iftype_valid = 'time'
        iftype_invalid = 'asdfasdf'

        #self.rw_sacobj.delta = 'stringisawrongtype'
        self.rw_sacobj.delta = delta
        self.assertAlmostEqual(self.rw_sacobj.delta, delta)

        self.rw_sacobj.iftype = iftype_valid
        self.assertEqual(self.rw_sacobj.iftype, iftype_valid)
        with self.assertRaises(ValueError): self.rw_sacobj.iftype = iftype_invalid

    def test_write_data(self):
        """
        Test changing data values
        """
        newdata = [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ]

        # readonly sacfile object should raise an error
        with self.assertRaises(IOError):
            self.ro_sacobj.data = newdata

        delta = self.rw_sacobj.delta
        begining = self.rw_sacobj.b
        newend =  begining + 9 * delta
        orgdata = self.rw_sacobj.data
        self.rw_sacobj.data = newdata
        self.new_sacobj.data = newdata
        self.assertEqual(self.rw_sacobj.data, newdata)
        self.assertEqual(self.new_sacobj.data, newdata)
        self.assertAlmostEqual(self.rw_sacobj.e, newend, places=5)

    def test_read_data(self):
        """
        Read data and check first 10 values
        """
        self.assertEqual(self.ro_sacobj.data[:10], [-1616.0, -1609.0, -1568.0, -1606.0, -1615.0, -1565.0, -1591.0, -1604.0, -1601.0, -1611.0])


if __name__ == '__main__':
    unittest.main()
