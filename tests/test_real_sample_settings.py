import unittest
import mock
import os
import logging

import bernielib as bl

from mock import patch

class bernielib_test_case(unittest.TestCase):
    
    @patch('time.sleep')
    @patch('serial.Serial')
    def setUp(self, mock_serial, mock_sleep):
        logging.disable(logging.CRITICAL)
        self.ber = bl.robot(cartesian_port_name='COM1', loadcell_port_name='COM2')
        self.s1 = bl.createSample('eppendorf', 's1', self.ber.samples_rack, 1, 0, 0)
        self.beads_5ml = bl.createSample('5mL', 'beads_5ml', self.ber.samples_rack, 1, 0, 0)
        
        self.eppendorf_mix_script_file_path = 'eppendorf_mix_script.csv'

    def test_eppendorf_settings_present(self):
        self.assertTrue(os.path.exists(self.s1.stype.name+'.json'))

    def test_5mL_settings_present(self):
        self.assertTrue(os.path.exists(self.beads_5ml.stype.name+'.json'))
        
    def test_eppendorf_mix_script_present(self):
        data = self.s1.stype.data
        self.assertIn('mix_script_file_path', data)

    def test_5mL_mix_script_present(self):
        data = self.beads_5ml.stype.data
        self.assertIn('mix_script_file_path', data)

    def tearDown(self):
        del self.ber
        del self.s1
        del self.beads_5ml
        logging.disable(logging.NOTSET)

if __name__ == '__main__':
    unittest.main()