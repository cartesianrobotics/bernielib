import pandas as pd
import os

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
    
    def setExtraImmersionVol(self, volume):
        """
        When uptaking the liquid from the sample, one shall insert the pipette deeper that 
        the desired volume, or else the pipette will uptake bubbles.
        This setting determines how much deeper to insert. 
        Inputs
            volume
                extra volume to insert the pipette, in uL.
                
        Example: from eppendorf tube, I want to get 200 uL of liquid. Currently, there is 1000 uL present.
        If I insert to 800 uL, the pipette will uptake bubbles. So I need to insert deeper. 
        if I provide volume=50, the pipette will go 50 uL deeper, meaning, to the 750 uL position.
        """
        self._setSetting('extra_immersion_volume', volume)
    
    def getExtraImmersionVol(self):
        return self._getSetting('extra_immersion_volume')
    
    def setCloseToBottomVol(self, volume):
        """
        If I need to uptake most of the liquid from the tube, I am risking to either hit the 
        bottom and not uptake anything, or wrongly estimate the real volume/real tube height, and 
        uptake bubbles. So to uptake, I need to perform speciall "near bottom uptake procedure".
        This setting informs the robot when to engage this procedure.
        """
        self._setSetting('close_to_bottom_volume', volume)
        
    def getCloseToBottomVol(self):
        return self._getSetting('close_to_bottom_volume')
    
    def setLowVolUptakeParameters(self, step, steps_number, delay):
        self._setSetting('low_vol_uptake_single_step', step)
        self._setSetting('low_vol_uptake_number_of_steps', steps_number)
        self._setSetting('low_vol_uptake_delay_between_steps', delay)
    
    def getLowVolUptakeParameters(self):
        step = self._getSetting('low_vol_uptake_single_step')
        steps_number = self._getSetting('low_vol_uptake_number_of_steps')
        delay = self._getSetting('low_vol_uptake_delay_between_steps')
        return step, steps_number, delay
        
    def setMixScriptFilePath(self, filepath):
        self._setSetting('mix_script_file_path', filepath)
        
    def getMixScriptFilePath(self):
        return self._getSetting('mix_script_file_path')
    
    def getMixScript(self, filepath=None):
        if filepath is None:
            filepath = self.getMixScriptFilePath()
        
        if os.path.exists(filepath):
            mix_script_df = pd.read_csv(filepath)
            return mix_script_df
        else:
            print("Function getMixScript; sample type "+str(self.name)+":")
            print("Provided path "+str(filepath)+" does not exist.")
    
    
class sample(data):
    """
    Class handling samples
    
    Class Q&A:
        Does the class has rack information?
            Yes, there are functions responsible for placing and removing sample to a rack.
            The rack object is passed and retrieved.
            Sample can be only in one rack at a time, the rack object is stored in self.rack
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
        z_top_abs = self.getSampleTopAbsZ(added_length=added_length)
        z = z_top_abs + z_relative_to_top
        return z
        
    def calcAbsLiquidLevelFromVol(self, volume, added_length=0):
        z_top_abs = self.getSampleTopAbsZ(added_length=added_length)
        z_relative = self.stype.getDepthFromVolume(volume)
        z = z_top_abs + z_relative
        return z
    
    def getCenterXY(self):
        col, row = self.getWell()
        x, y = self.rack.calcWellXY(col, row)
        return x, y        
        
    def dump(self):
        """
        Destroys sample, and removes its data from the drive
        Use it when you need to state during the protocol that the sample is never going to be needed, or used up.
        """
        self.purge()
    
    def setExtraImmersionVol(self, volume):
        """
        Overrides the setting from the sample type class
        """
        self._setSetting('extra_immersion_volume', volume)
    
    def getExtraImmersionVol(self):
        if self._settingPresent('extra_immersion_volume'):
            return self._getSetting('extra_immersion_volume')
        else:
            return self.stype.getExtraImmersionVol()
            
    def _allowDry(self, volume):
        if volume >= self.getVolume():
            return True
        else:
            return False
            
    def _allowPlungerLagCompensation(self, v_uptake, v_lag):
        v_total = self.getVolume()
        v_lag_allowed = v_total - v_uptake
        if v_lag_allowed > v_lag:
            return v_lag
        elif v_lag_allowed < v_lag and v_lag_allowed > 0:
            return v_lag_allowed
        else:
            return 0
            
    def _isLowVolumeUptakeNeeded(self, v_uptake):
        """
        Determine whether robot needs to perform low volume uptake procedure
        """
        v_total = self.getVolume()
        v_extra_immers = self.getExtraImmersionVol()
        v_immers = v_uptake + v_extra_immers
        v_remain = v_total - v_immers
        v_threshold = self.getCloseToBottomVol()
        
        if v_threshold < v_remain:
            # Enough liquid
            return False
        else:
            return True
            
        
    def calcNormalPipettingZ(self, v_uptake, v_lag, added_length):
        v_total = self.getVolume()
        v_lag = self._allowPlungerLagCompensation(v_uptake, v_lag)
        v_extra_immers = self.getExtraImmersionVol()
        v_immers = v_total - v_uptake - v_lag - v_extra_immers
        z = self.calcAbsLiquidLevelFromVol(v_immers, added_length=added_length)
        return z
        

    def setPipettingDelay(self, delay):
        self._setSetting('pipetting_delay', delay)
    
    def getPipettingDelay(self):
        return self._getSetting('pipetting_delay')        
    
    def setZBottom(self, z):
        """
        Sets absolute Z coordinate of the bottom of the tube.
        This is the coordinate at which robot will physically touch the bottom with specified force.
        """
        self._setSetting('tube_bottom_z', z)
        
    def getZBottom(self):
        """
        Returns absolute Z coordinate of the bottom of the tube, at which the robot will physically press into the bottom.
        Assumed the robot has a tip attached.
        At this level pipetting will likely fail; you need to lift the robot 0.5 mm up or more.
        """
        return self._getSetting('tube_bottom_z')
    
    def setCloseToBottomVol(self, v):
        """
        Set the volume at which robot will perform "low volume" operations; such as 
        touching the bottom in order to find its precise coordinates.
        
        Overrides the setting for the sample type. 
        
        Use it so robot won't touch bottom every time for the same sample, wasting time.
        """
        self._setSetting('close_to_bottom_volume', v)
        
    def getCloseToBottomVol(self):
        """
        Returns the volume at which robot will perform "low volume" operations.
        Don't confuse with the same setting for sample type; this function sets it for the individual sample.
        
        Use it so robot does not have to touch bottom of the tube every time.
        """
        if self._settingPresent('close_to_bottom_volume'):
            v = self._getSetting('close_to_bottom_volume')
        else:
            # If the setting was not specified for the specific sample, use sample type 
            # to obtain this setting instead.
            v = self.stype.getCloseToBottomVol()
        return v

    def getCloseToBottomZ(self, tip_length_compensation):
        approx_vol = self.getCloseToBottomVol()
        approx_z = self.calcAbsLiquidLevelFromVol(approx_vol, added_length=tip_length_compensation)
        return approx_z

        
    def setBottomTouched(self):
        """
        Called when robot performed at least one approach Z to bottom.
        """
        self._setSetting('robot_touched_sample_bottom', 1)
        



def createSample(type_name, sample_name, rack, pos_col, pos_row, volume, purge=True):

    if sample_name == 'waste':
        print("You can't use this sample_name, because it interferes with the internal settings.")
        print("Please chose different sample_name.")
        return
    stype = sample_type(type_name)
    s = sample(sample_name, stype)
    if purge:
        # If dealing with a new sample, program purges all settings that may have been left
        # from the old sample.
        s.purge()
        s = sample(sample_name, stype)
    s.place(rack, pos_col, pos_row)
    s.setVolume(volume)
    return s
    

def createSamplesToPurifyList(robot, volume_list=None, position_list=None, 
                              number_of_tubes=None, start_from_position=0):
    """
    Initializes a list of samples. 
    Can be used both for the samples to purify and for the intermediary samples.
    
    Inputs:
        robot
            Bernie robot instance
        volume_list
            List of volumes of liquid that is already in the sample. If not provided, assumed empty tube.
        position_list
            Custom list of positions that every tube has. If not provided, assume that the tubes
            are at position 0, 1, 2, ...
        number_of_tubes
            when volume_list is not provided, the function will initialize that many tubes with 0 volume.
        start_from_position
            Unless position_list is provided, the function will start initializing the tubes from that position.
            For example, when start_from_position=6, the first sample will be initialized at the well (1, 6).
    """

    type_name = 'eppendorf'
    rack = robot.samples_rack
    
    sample_list = []
    
    # Checking if volume list is provided. If not, creating zero volumes list
    if volume_list is None:
        # Checking if number of tubes provided
        if number_of_tubes is None:
            print("Error: Provide either number of tubes, or list of volumes in the tubes.")
            return
        volume_list = []
        for i in range(number_of_tubes):
            volume_list.append(0)
    
    # If custom position list is not provided, I am generating a new position list starting from 0 well.
    if position_list is None:
        sample_counter = start_from_position
        position_list = []
        for volume in volume_list:
            position_list.append(sample_counter)
            sample_counter += 1
    
    
    
    # Now initializing the sample instances.
    for volume, position in zip(volume_list, position_list):
        sample_name = 'sample'+str(position)
        s = createSample(type_name, sample_name, rack, pos_col=1, pos_row=position, volume=volume)
        sample_list.append(s)
        
    return sample_list
    

def createPurifiedSamplesList(robot, number, row_start=0):
    type_name = 'eppendorf'
    rack = robot.samples_rack
    
    sample_counter = 0
    sample_list = []
    
    for i in range(number):
        sample_name = 'purified'+str(sample_counter)
        # Starting with 0 volume, liquid will be there after purification.
        s = createSample(type_name, sample_name, rack, pos_col=0, pos_row=row_start, volume=0)
        sample_list.append(s)
        sample_counter += 1
        row_start += 1 # Every next sample is occupying a new row
        
    return sample_list
    

# TODO: create sample list for intermediate tubes