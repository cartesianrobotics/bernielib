import unittest
import os
import mock
import json
import shutil

import general


class settings_test_case(unittest.TestCase):
    
    def setUp(self):
    
        # Running teardown to get rid of leftover files (if any):
        self.tearDown()
        
        # Creating a settings dir for the test
        mock_data = {
            'the_other_setting': 38,
        }
        
        mock_factory_data = {
            'the_other_settings': 22,
            'setting_only_in_factory_default': 19,
        }
        
        self.name = 'dummy_setting_name'
        
        f = open(self.name+'.json', 'w')
        f.write(json.dumps(mock_data))
        f.close()
        
        try:
            os.mkdir('./factory_default_for_test_purposes/')
        except:
            print("Factory setting directory existed from the last try")
        
        f = open('./factory_default_for_test_purposes/'+self.name+'.json', 'w')
        f.write(json.dumps(mock_factory_data))
        f.close()
        
        self.dummy_obj = general.data(self.name)
        

    def test_settings_init(self):
        # Settings file shouldn't exist before the init
        self.assertFalse(os.path.exists('setting_file_creation_test.json'))
        dummy_obj = general.data('setting_file_creation_test')
        # Settings file should appear at the init
        self.assertTrue(os.path.exists('setting_file_creation_test.json'))

    def test__setSetting(self):
        
        # Setting should not exist from the start
        self.assertFalse(self.dummy_obj._settingPresent('this_one_setting'))
        
        self.dummy_obj._setSetting('this_one_setting', 42)
        
        self.assertTrue(self.dummy_obj._settingPresent('this_one_setting'))
        setting_value = self.dummy_obj._getSetting('this_one_setting')
        self.assertEqual(setting_value, 42)
    
    def test__request_nonexisting_setting(self):
        self.assertFalse(self.dummy_obj._settingPresent('this_one_setting'))
        self.assertIsNone(self.dummy_obj._getSetting('this_one_setting'))
        

    def test__request_existing_setting(self):
        self.assertTrue(self.dummy_obj._settingPresent('the_other_setting'))
        self.assertEqual(self.dummy_obj._getSetting('the_other_setting'), 38)


    def test__loadFactoryDefault(self):
        # For the test purpose, replacing the real factory default path with the mock one.
        self.dummy_obj.factory_default_path = './factory_default_for_test_purposes/'+self.name+'.json'
        data = self.dummy_obj.loadFactoryDefault()
        expected_data = {
            'the_other_settings': 22,
            'setting_only_in_factory_default': 19,
        }
        self.assertEqual(data, expected_data)
        value = data['setting_only_in_factory_default']
        self.assertEqual(value, 19)

        
    def test__request_setting_that_are_only_in_factory_defaults(self):
        # For the test purpose, replacing the real factory default path with the mock one.
        self.dummy_obj.factory_default_path = './factory_default_for_test_purposes/'+self.name+'.json'
        self.assertFalse(self.dummy_obj._settingPresent('setting_only_in_factory_default'))
        self.assertEqual(self.dummy_obj._getSetting('setting_only_in_factory_default'), 19)
        # After the program attempts to get a setting that is only present in factory defaults,
        # the local settings must be updated, and the requested setting must appear there.
        self.assertTrue(self.dummy_obj._settingPresent('setting_only_in_factory_default'))
        

    def test__internal_factory_default_mock_exist(self):
        self.assertTrue(os.path.exists('./factory_default_for_test_purposes/'+self.name+'.json'))

    
    def tearDown(self):
        try:
            os.remove('dummy_setting_name.json')
        except:
            pass
        try:
            os.remove('setting_file_creation_test.json')
        except:
            pass
        try:
            os.remove('./factory_default_for_test_purposes/'+self.name+'.json')
        except:
            pass
        try:
            os.rmdir('./factory_default_for_test_purposes/')
        except:
            pass