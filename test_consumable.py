import os
import json

import unittest
import mock
from mock import patch

import bernielib as bl


def removeOldTestFile():
    try:
        os.remove('test_consumable.json')
    except:
        pass
        
class bernielib_test_case(unittest.TestCase):

    @patch('bernielib.consumable._setSetting')
    @patch('bernielib.consumable._getReadyList')
    def test_consume(self, mock__getReadyList, mock_setSetting):
        tips_rack = bl.consumable('tips')
        tips_rack._getReadyList.return_value = [[0,0], [0,1], [0,2]]
        tips_rack.consume(col=0,row=0)
        tips_rack._setSetting.assert_called_with('unused_consumable_list', [[0,1], [0,2]])
        
    
    
    def test_consumable_settings_file_gets_created(self):
        
        removeOldTestFile()
        
        c = bl.consumable('test_consumable')
        c.save()

        # Control for the file to be created
        try:
            f = open('test_consumable.json', 'r')
            successfully_opened = True
            f.close()
        except:
            successfully_opened = False
        self.assertEqual(successfully_opened, True)
        
        # Negative control for some random file not to be created
        try:
            f = open('negative_control_consumable.json', 'r')
            successfully_opened = True
            f.close()
        except:
            successfully_opened = False
        self.assertEqual(successfully_opened, False)
        
        removeOldTestFile()
            
        # Control for test file to be successfully deleted
        try:
            f = open('test_consumable.json', 'r')
            successfully_opened = True
            f.close()
        except:
            successfully_opened = False
        self.assertEqual(successfully_opened, False)



    def test_next(self):
        removeOldTestFile()
        
        c = bl.consumable('test_consumable')
        c._setSetting('wells_x', 12)
        c._setSetting('wells_y', 8)
        c.refill()
        
        # Generating test list
        l=[]
        for i in range(12):
            for j in range(8):
                l.append([i, j])
        
        for element in l:
            col, row = c.next()
            self.assertEqual(element, [col, row])
    
        removeOldTestFile()


    def test_next_saving_unused_consumables(self):
        removeOldTestFile()
        
        c = bl.consumable('test_consumable')
        c._setSetting('wells_x', 12)
        c._setSetting('wells_y', 8)
        c.refill()
        del c
        
        # Generating test list
        l=[]
        for i in range(12):
            for j in range(8):
                l.append([i, j])

        for element in l:
            c = bl.consumable('test_consumable')
            col, row = c.next()
            self.assertEqual(element, [col, row])
            del c

        removeOldTestFile()


    def test_next__typles_turning_to_list_bug(self):
        """
        I had a bug which causes tuples of (col, row) turn to list [col, row]
        in rack setting file. 
        This one tests for the bug
        """
        removeOldTestFile()
        
        c = bl.consumable('test_consumable')
        c._setSetting('wells_x', 12)
        c._setSetting('wells_y', 8)
        c.refill()
        
        self.assertEqual(c.data['unused_consumable_list'][0], [0,0])
        
        f = open('test_consumable.json', 'r')
        data = json.loads(f.read())
        f.close()
        
        self.assertEqual(data['unused_consumable_list'][0], [0,0])
        
        
        

if __name__ == '__main__':
    unittest.main()