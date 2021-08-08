import unittest
import mock

import bernielib as bl

class bernielib_test_case(unittest.TestCase):

    def test_isLowVolumeUptakeNeeded(self):
        bl.time.sleep = mock.MagicMock()
        bl.serial.Serial = mock.MagicMock()
        ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 1000)
        self.assertEqual(s1.getCloseToBottomVol(), 50)
        self.assertEqual(s1.getVolume(), 1000)
        self.assertEqual(s1.getExtraImmersionVol(), 200)
        
        low_volume_uptake_needed = s1._isLowVolumeUptakeNeeded(0)
        self.assertFalse(low_volume_uptake_needed)
        low_volume_uptake_needed = s1._isLowVolumeUptakeNeeded(250)
        self.assertFalse(low_volume_uptake_needed)
        
        s1 = bl.createSample('eppendorf', 's1', ber.samples_rack, 1, 0, 200)
        low_volume_uptake_needed = s1._isLowVolumeUptakeNeeded(0)
        self.assertTrue(low_volume_uptake_needed)
        


if __name__ == '__main__':
    unittest.main()