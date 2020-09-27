# Local files
from general import data


class sample_type(data):
    """
    Class handling sample types
    """
    def __init__(self, name):
        super().__init__(name=name)
        
    def _setZAboveRacks(self, z_above_racks_dict):
        self._setSetting('z_above_racks_dict', z_above_racks_dict)
        
    def _getZAboveRacks(self):
        return self._getSetting('z_above_racks_dict')
        
    def setZAboveSpecificRack(self, rack, z):
        try:
            z_above_racks_dict = self._getZAboveRacks()
        except:
            z_above_racks_dict = {}
        z_above_racks_dict[rack.name] = z
        self._setZAboveRacks(z_above_racks_dict)
        
    def getZAboveSpecificRack(self, rack):
        z_above_racks_dict = self._getZAboveRacks()
        z = z_above_racks_dict[rack.name]
        return z
    
    def setInnerDiameter(self, d):
        self._setSetting('inner_diameter', d)
        
    def getInnerDiameter(self):
        return self._getSetting('inner_diameter')
    
    
    def setDepth(self, d):
        """
        Sets the sample depth in mm. Measured from the very top of the sample,
        to the inner bottom.
        In other words: let z_top be a coordinate when the robot (with tip) would hit the top rim
        of the sample, and z_bottom is the coordinate where the robot hits the very bottom of the sample.
        Then, d = z_bottom - z_top
        """
        self._setSetting('depth', d)
        
    def getDepth(self):
        return self._getSetting('depth')
        
        
    def setDepthToVolRelation(self, depth_to_vol_dict):
        """
        Sets the relation between sample volume and distance from the top of the sample to the
        liquid level.
        """
        self._setSetting('depth_to_vol_dict', depth_to_vol_dict)
        
    def getDepthToVolRelation(self):
        return self._getSetting('depth_to_vol_dict')
    
    def getDepthFromVolume(self, volume):
        """
        Calculates distance from the tube top to the level of the liquid of provided volume
        It uses saved relation between depth and volumes; calculating 
        current depth using linear approximation.
        For example, if 5000 uL of liquid will be at 50 mm from top, 10000 uL of liquid at 40 mm from top, 
        then if volume = 7500 (uL), function will return 45 (mm).
        """
        depth_to_vol_dict = self.getDepthToVolRelation()
        # Calculating differences between provided volume and all the standard volumes
        # This is to find closest standard data points to use for depth calculation.
        diff_dict = {}
        for key in depth_to_vol_dict.keys():
            standard_vol = float(key)
            diff = abs(standard_vol - volume)
            diff_dict[key] = diff
        # First standard data point (closest to the provided volume)
        standard_v_1 = min(diff_dict, key=diff_dict.get)
        diff_dict.pop(standard_v_1, None) # Removing 1st point from temp dict
        # Second standard data point (second closest to the provided volume)
        standard_v_2 = min(diff_dict, key=diff_dict.get)
        
        # Depths values associated with the standard volumes:
        standard_d_1 = depth_to_vol_dict[standard_v_1]
        standard_d_2 = depth_to_vol_dict[standard_v_2]
        
        # Now calculating linear relation
        p = [float(standard_v_1), standard_d_1]
        q = [float(standard_v_2), standard_d_2]
        
        a = q[1] - p[1]
        b = p[0] - q[0]
        c = a * p[0] + b * p[1]
        
        depth = (c - a * volume) / b
        
        return depth
        
    
    def getMaxVolume(self):
        depth_to_vol_dict = self.getDepthToVolRelation()
        vols_list = [float(x) for x in depth_to_vol_dict.keys()]
        max_vol = max(vols_list)
        return max_vol
    
    
    
    
    
class sample(data):
    """
    Class handling samples
    """
    
    def __init__(self, sname, stype, volume=None):
        super().__init__(name=sname)
        
        self.stype = stype # Object of a class sample_type
        if volume is not None:
            self.setVolume(volume)
        
    
    def setVolume(self, volume):
        self._setSetting('volume', volume)
        
    def getVolume(self):
        return self._getSetting('volume')
        
    def place(self, rack, x, y):
        self.rack = rack
        self._setSetting('rack_name', self.rack.name)
        self._setSetting('rack_x_well', x)
        self._setSetting('rack_y_well', y)
    
    
    def getWell(self):
        return self._getSetting('rack_x_well'), self._getSetting('rack_y_well')

    
    def getZAboveRack(self):
        return self.stype.getZAboveSpecificRack(self.rack)
        
    def getSampleTopAbsZ(self, added_length=0):
        """
        Returns absolute Z coordinate of the sample top
        """
        z_rack = self.rack.getZ(added_length=added_length)
        delta_z = self.getZAboveRack()
        z_sample_top = z_rack - delta_z
        return z_sample_top
        
    def calcSampleAbsZFromZRelativeToTop(self, z_relative_to_top, added_length=0):
        z_top_abs = self.getSampleTopAbsZ(self, added_length=added_length)
        z = z_top_abs + z_relative_to_top
        return z
        
    def calcAbsLiquidLevelFromVol(self, volume, added_length=0):
        z_top_abs = self.getSampleTopAbsZ(self, added_length=added_length)
        z_relative = self.stype.getDepthFromVolume(volume)
        z = z_top_abs + z_relative
        return z
    
    def getSampleCenterXY(self):
        col, row = self.getWell()
        x, y = self.rack.calcWellXY(col, row)
        return x, y