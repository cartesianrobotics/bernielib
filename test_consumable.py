import unittest
import mock

import bernielib as bl


class bernielib_test_case(unittest.TestCase):

    def test_consume(self):
        tips_rack = bl.consumable('tips')
        
        tips_rack._getReadyList = mock.MagicMock()
        tips_rack._getReadyList.return_value = [(0,0), (0,1), (0,2)]
        tips_rack._setSetting = mock.MagicMock()
        
        tips_rack.consume(col=0,row=0)
        
        tips_rack._setSetting.assert_called_with('unused_consumable_list', [(0,1), (0,2)])
        


if __name__ == '__main__':
    unittest.main()