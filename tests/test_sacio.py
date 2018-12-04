#!/usr/bin/env python

import unittest
import os
import tempfile
import shutil
from pysmo import SacIO

class sacioTestCase(unittest.TestCase):
    """Tests for `sacio.py`."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        testfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
        self.old_file = os.path.join(self.tmpdir, 'old.sac')
        self.new_file = os.path.join(self.tmpdir, 'new.sac')
        shutil.copyfile(testfile, self.old_file)
        self.old_sacobj = SacIO()
        self.old_sacobj.read(self.old_file)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_add_data_to_new_instance(self):
        newdata = [132, 232, 3465, 111]
        empty_sacobj = SacIO()
        empty_sacobj.data = newdata
        self.assertEqual(empty_sacobj.data, newdata)
        self.assertEqual(empty_sacobj.b, 0.0)

    def test_read_headers(self):
        """
        Read header values in our test file and
        check if they match the expected value.
        """
        self.assertEqual(self.old_sacobj.npts, 180000)
        self.assertAlmostEqual(self.old_sacobj.b, 53.060001373291016)
        self.assertAlmostEqual(self.old_sacobj.e, 3653.0400390625)
        self.assertEqual(self.old_sacobj.iftype, 'time')
        self.assertTrue(self.old_sacobj.leven)
        self.assertAlmostEqual(self.old_sacobj.delta, 0.02)
        with self.assertRaises(ValueError): self.old_sacobj.odelta
        self.assertEqual(self.old_sacobj.idep, 'unkn')
        self.assertAlmostEqual(self.old_sacobj.depmin, -8293.0)
        self.assertAlmostEqual(self.old_sacobj.depmax, 3302.0)
        self.assertAlmostEqual(self.old_sacobj.depmen, -572.200439453125)
        self.assertAlmostEqual(self.old_sacobj.o, 0.0)
        with self.assertRaises(ValueError): self.old_sacobj.a
        with self.assertRaises(ValueError): self.old_sacobj.t0
        with self.assertRaises(ValueError): self.old_sacobj.t1
        with self.assertRaises(ValueError): self.old_sacobj.t2
        with self.assertRaises(ValueError): self.old_sacobj.t3
        with self.assertRaises(ValueError): self.old_sacobj.t4
        with self.assertRaises(ValueError): self.old_sacobj.t5
        with self.assertRaises(ValueError): self.old_sacobj.t6
        with self.assertRaises(ValueError): self.old_sacobj.t7
        with self.assertRaises(ValueError): self.old_sacobj.t8
        with self.assertRaises(ValueError): self.old_sacobj.t9
        with self.assertRaises(ValueError): self.old_sacobj.f
        # kzdate is a derived header
        # kztime is a derived header
        self.assertEqual(self.old_sacobj.iztype, 'o')
        with self.assertRaises(ValueError): self.old_sacobj.kinst
        with self.assertRaises(ValueError): self.old_sacobj.resp0
        with self.assertRaises(ValueError): self.old_sacobj.resp1
        with self.assertRaises(ValueError): self.old_sacobj.resp2
        with self.assertRaises(ValueError): self.old_sacobj.resp3
        with self.assertRaises(ValueError): self.old_sacobj.resp4
        with self.assertRaises(ValueError): self.old_sacobj.resp5
        with self.assertRaises(ValueError): self.old_sacobj.resp6
        with self.assertRaises(ValueError): self.old_sacobj.resp7
        with self.assertRaises(ValueError): self.old_sacobj.resp8
        with self.assertRaises(ValueError): self.old_sacobj.resp9
        with self.assertRaises(ValueError): self.old_sacobj.kdatrd
        self.assertEqual(self.old_sacobj.kstnm, 'MEL01')
        self.assertAlmostEqual(self.old_sacobj.cmpaz, 0)
        self.assertAlmostEqual(self.old_sacobj.cmpinc, 90)
        with self.assertRaises(ValueError): self.old_sacobj.istreg
        self.assertAlmostEqual(self.old_sacobj.stla, -43.855464935302734)
        self.assertAlmostEqual(self.old_sacobj.stlo, -73.74272155761719)
        with self.assertRaises(ValueError): self.old_sacobj.stel
        with self.assertRaises(ValueError): self.old_sacobj.stdp
        self.assertEqual(self.old_sacobj.kevnm, '043550359BHN')
        with self.assertRaises(ValueError): self.old_sacobj.ievreg
        self.assertAlmostEqual(self.old_sacobj.evla, -15.265999794006348)
        self.assertAlmostEqual(self.old_sacobj.evlo, -75.20800018310547)
        with self.assertRaises(ValueError): self.old_sacobj.evel
        self.assertAlmostEqual(self.old_sacobj.evdp, 30.899999618530273)
        self.assertEqual(self.old_sacobj.ievtyp, 'quake')
        self.assertEqual(self.old_sacobj.khole, '')
        self.assertAlmostEqual(self.old_sacobj.dist, 3172.399658203125)
        self.assertAlmostEqual(self.old_sacobj.az, 177.77978515625)
        self.assertAlmostEqual(self.old_sacobj.baz, 357.0372619628906)
        self.assertAlmostEqual(self.old_sacobj.gcarc, 28.522098541259766)
        self.assertTrue(self.old_sacobj.lovrok)
        with self.assertRaises(ValueError): self.old_sacobj.iqual
        with self.assertRaises(ValueError): self.old_sacobj.isynth
        with self.assertRaises(ValueError): self.old_sacobj.user0
        with self.assertRaises(ValueError): self.old_sacobj.user1
        with self.assertRaises(ValueError): self.old_sacobj.user2
        with self.assertRaises(ValueError): self.old_sacobj.user3
        with self.assertRaises(ValueError): self.old_sacobj.user4
        with self.assertRaises(ValueError): self.old_sacobj.user5
        with self.assertRaises(ValueError): self.old_sacobj.user6
        with self.assertRaises(ValueError): self.old_sacobj.user7
        self.assertAlmostEqual(self.old_sacobj.user8, 4.900000095367432)
        self.assertAlmostEqual(self.old_sacobj.user9, 5.000000)
        with self.assertRaises(ValueError): self.old_sacobj.kuser0
        with self.assertRaises(ValueError): self.old_sacobj.kuser1
        with self.assertRaises(ValueError): self.old_sacobj.kuser2
        with self.assertRaises(ValueError): self.old_sacobj.nxsize
        with self.assertRaises(ValueError): self.old_sacobj.xminimum
        with self.assertRaises(ValueError): self.old_sacobj.xmaximum
        with self.assertRaises(ValueError): self.old_sacobj.nysize
        with self.assertRaises(ValueError): self.old_sacobj.yminimum
        with self.assertRaises(ValueError): self.old_sacobj.ymaximum
        self.assertEqual(self.old_sacobj.nvhdr, 6)
        with self.assertRaises(ValueError): self.old_sacobj.scale
        self.assertEqual(self.old_sacobj.norid, 0)
        self.assertEqual(self.old_sacobj.nevid, 0)
        self.assertEqual(self.old_sacobj.nwfid, 13)
        with self.assertRaises(ValueError): self.old_sacobj.iinst
        self.assertTrue(self.old_sacobj.lpspol)
        self.assertTrue(self.old_sacobj.lcalda)
        self.assertEqual(self.old_sacobj.kcmpnm, 'BHN')
        self.assertEqual(self.old_sacobj.knetwk, 'YJ')
        with self.assertRaises(ValueError): self.old_sacobj.mag
        with self.assertRaises(ValueError): self.old_sacobj.imagtyp
        with self.assertRaises(ValueError): self.old_sacobj.imagsrc

        # try reading non-existing header
        with self.assertRaises(AttributeError): self.old_sacobj.nonexistingheader

    def test_read_data(self):
        """
        Read data and check first 10 values
        """
        self.assertEqual(self.old_sacobj.data[:10], [-1616.0, -1609.0, -1568.0, -1606.0, -1615.0, -1565.0, -1591.0, -1604.0, -1601.0, -1611.0])

    def test_change_headers(self):
        """
        Test changing header values
        """
    
        olddelta = self.old_sacobj.delta
        newdelta = 0.123
    
        iftype_valid = 'time'
        iftype_invalid = 'asdfasdf'
        
        self.old_sacobj.delta = newdelta
        self.assertAlmostEqual(self.old_sacobj.delta, newdelta)
        self.old_sacobj.delta = olddelta
    
        self.old_sacobj.iftype = iftype_valid
        self.assertEqual(self.old_sacobj.iftype, iftype_valid)
        with self.assertRaises(ValueError): self.old_sacobj.iftype = iftype_invalid

        # Try writing a boolean to a header field that should only accept strings
        with self.assertRaises(ValueError): self.old_sacobj.kuser0 = True

        # Try writing a string that is too long
        with self.assertRaises(ValueError): self.old_sacobj.kuser0 = 'too long string'

    def test_change_data_and_write_to_file(self):
        """
        Test changing data values
        """
        newdata = [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ]
    
        delta = self.old_sacobj.delta
        begining = self.old_sacobj.b
        newend =  begining + 9 * delta
        orgdata = self.old_sacobj.data
        self.old_sacobj.data = newdata
        self.assertEqual(self.old_sacobj.data, newdata)
        self.assertAlmostEqual(self.old_sacobj.e, newend, places=5)
    
        # write changes to new sac file
        self.old_sacobj.write(self.new_file)

        # open the new file to a new sac object
        self.new_sacobj = SacIO.from_file(self.new_file)
        self.assertEqual(self.new_sacobj.data, newdata)
        self.assertAlmostEqual(self.new_sacobj.depmin, 1.0)
        self.assertAlmostEqual(self.new_sacobj.depmax, 10.0)
        self.assertAlmostEqual(self.new_sacobj.depmen, 5.5)


if __name__ == '__main__':
    unittest.main()
