import serial
import time
import re
import logging
import sys
import json


#TODO: Tip end correction


"""
Low level communication library with a device connected through serial port.

Part of BernieLib.

Sergii Pochekailov
"""

# Those are parameters for serial connection. 
# Used when opening serial port.
BAUDRATE = 115200
TIMEOUT = 0.1   # seconds
END_OF_LINE = "\r"


def listSerialPorts():
    """ 
    Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


class robot():
    """
    Handles all robot operations
    """
    
    def __init__ (self, cartesian_port_name, pipette_port_name, misc_port_name):
        
        self.data = {}
        self.recent_message = ''
        self.name = 'robot'
        
        self.loadData()
        
        # Initializing racks for the robot
        self.samples_rack = rack('samples')
        self.waste_rack = rack('waste')
        self.tips_rack = rack('tips')
        self.reagents_rack = rack('reagents')
        
        # Opening communications
        self.cartesian_port = serial.Serial(cartesian_port_name, BAUDRATE, timeout=TIMEOUT)
        self.pipette_port = serial.Serial(pipette_port_name, BAUDRATE, timeout=TIMEOUT)
        self.misc_port = serial.Serial(misc_port_name, BAUDRATE, timeout=TIMEOUT)
        
        # Waiting for ports to open
        time.sleep(1)
        
        self.cartesian_port.flushInput()
        self.pipette_port.flushInput()
        self.misc_port.flushInput()
        
        # Starting with tip not attached
        self.tip_attached = 0 # 0 - not attached, 1 - attached
        
    
    def close(self):
        try:
            self.cartesian_port.close()
        except:
            pass
        try:
            self.pipette_port.close()
        except:
            pass
        try:
            self.misc_port.close()
        except:
            pass
    
    
    
    
    def _readAll(self, port):
        time.sleep(0.05)
        message = ''
        while port.inWaiting():
            message += port.read(1).decode("utf-8")
            
        return message
    
    
    def _readUntilMatch(self, port, pattern):
        message = ''
        while True:
            message += self._readAll(port)
            if re.search(pattern=pattern, string=message):
                self.recent_message = message
                break
        return self.recent_message
    
    
    def _write(self, port, expression, eol):
        port.flushInput()
        expression = expression.strip()
        expression = expression + eol
        expr_enc = expression.encode()
        port.write(expr_enc)
    
        
    def writeMisc(self, expression):
        self._write(port=self.misc_port, expression=expression, eol='')
    
        
    def _writeAndWait(self, port, expression, eol, confirm_message):
        self._write(port, expression, eol)
        message = self._readUntilMatch(port, confirm_message)
        return message
        
    
    def writeAndWaitMisc(self, expression):
        return self._writeAndWait(port=self.misc_port, expression=expression, eol='', confirm_message='\r\n')


    def _getRackObjectByName(self, rack_name):
        """
        Returns rack object using its name. Possible rack values: 'samples', 'waste', 'tips', 'reagents'.
        """
        # getting a rack object
        if rack_name == 'samples':
            r = self.samples_rack
        elif rack_name == 'waste':
            r = self.waste_rack
        elif rack_name == 'tips':
            r = self.tips_rack
        elif rack_name == 'reagents':
            r = self.reagents_rack
        else:
            print ("Please provide valid rack value")
            print ("Possible values: 'samples', 'waste', 'tips', 'reagents'.")
            return
        return r

    
# ==========================================================================================
# Pipette functions
    

    def writePipette(self, expression):
        self._write(port=self.pipette_port, expression=expression, eol='\r')    
    
    
    def writeAndWaitPipette(self, expression, confirm_message="Idle"):
        """
        Function will write an expression to the device and wait for the proper response.
        
        Use this function to make the devise perform a physical operation and
        make sure program continues after the operation is physically completed.
        
        Function will return an output message
        """
        self.writePipette(expression)
        
        full_message = ""
        while True:
            message = self._readAll(self.pipette_port)
            if message != "":
                full_message += message
                if re.search(pattern=confirm_message, string=full_message):
                    break
            self.writePipette("?")
            
    
    def pipetteSetSpeed(self, speed):
        self.writePipette('$110='+str(speed))
    
    
    def pipetteHome(self):
        self.writeAndWaitPipette('$H')
        self.pipetteServoUp()
        
    
    def pipetteUnlock(self):
        self.writeAndWaitPipette('$X')
    
    
    def pipetteMove(self, dist):
        dist = dist * -1.0
        self.writeAndWaitPipette('G0 X'+str(dist))
        
    
    def pipetteServoUp(self):
        self.writeAndWaitPipette('M3 S90')
        
    
    def pipetteServoDown(self):
        self.writeAndWaitPipette('M5')
    
    
    def setTipLength(self, length):
        """
        Specifies added length of the tip, when it is attached to the pipettor
        """
        self._setSetting('added_tip_length', length)
    
    
    def getTipLength(self):
        """
        Returns the length of the tip. 
        This is how much longer the pipette become after attaching a tip.
        """
        return self._getSetting('added_tip_length')
    
    
    def pickUpTip(self, column, row, fine_approach_dz=10, raise_z=0, raise_dz_with_tip=60):
        # Moving towards the tip
        self.moveToWell(rack_name='tips', column=column, row=row, save_height=fine_approach_dz)
        # Moving down while controlling the pressure
        self.moveDownUntilPress(1, 4000)
        # Moving up with the tip
        self.moveAxisDelta('Z', -raise_dz_with_tip)
        self.tip_attached = 1
    
    
    def dumpTip(self):
        self.pipetteServoDown()
        self.pipetteMove(40)
        self.tip_attached = 0
        self.pipetteMove(1)
        self.pipetteServoUp()
        
    
    
# ================================================================================
# Load cells (pressure sensors) functions
    
    
    def tareAll(self):
        self.writeMisc('T')
    
    
    def readRightLoad(self):
        return float(self.writeAndWaitMisc('RR').strip())
    
    
    def readLeftLoad(self):
        return float(self.writeAndWaitMisc('RL').strip())
    

    def getCombinedLoad(self):
        return self.readRightLoad() + self.readLeftLoad()
    
# ===================================================================================
# Magnetic rack functions
    
    
    def rackPowerOn(self):
        self.writeAndWaitMisc('P on')
    
    
    def rackPowerOff(self):
        self.writeAndWaitMisc('P off')
        
        
    def rackMoveMagnetsAngle(self, angle):
        self.writeAndWaitMisc('G0 '+str(angle))

        
    def setMagnetsAwayAngle(self, angle):
        self._setSetting('magnets_away_angle', angle)
    
    
    def setMagnetsNearTubeAngle(self, angle):
        self._setSetting('magnets_near_tube_angle', angle)
    
    
    def getMagnetsAwayAngle(self):
        return self._getSetting('magnets_away_angle')
        
    
    def getMagnetsNearTubeAngle(self):
        return self._getSetting('magnets_near_tube_angle')
    
    
    def moveMagnetsAway(self, poweroff=False):
        self.rackPowerOn()
        self.rackMoveMagnetsAngle(self.getMagnetsAwayAngle())
        if poweroff:
            #time.sleep(1)
            self.rackPowerOff()
    
    
    def moveMagnetsTowardsTube(self, poweroff=False):
        self.rackPowerOn()
        self.rackMoveMagnetsAngle(self.getMagnetsNearTubeAngle())
        if poweroff:
            self.rackPowerOff()

            
# ===========================================================================
# Cartesian robot functions


    def writeCartesian(self, expression):
        self._write(port=self.cartesian_port, expression=expression, eol='\r')


    def writeAndWaitCartesian(self, expression):
        return self._writeAndWait(port=self.cartesian_port, expression=expression, eol='\r', confirm_message='ok\n')

    
    def home(self, part='all'):
        if part == 'robot':
            self.robotHome()
        elif part == 'pipette':
            self.pipetteHome()
        elif part == 'magrack':
            self.moveMagnetsAway()
        else:
            self.robotHome()
            self.pipetteHome()
            self.moveMagnetsAway()
            
    
    def robotHome(self, axis=None):
        try:
            axis = axis.upper()
        except:
            pass
        if axis is None:
            self.writeAndWaitCartesian('G28 Z')
            self.writeAndWaitCartesian('G28 XY')
        else:
            self.writeAndWaitCartesian('G28 '+axis)
    
    
    def getSpeed(self, axis):
        if axis == 'X' or axis == 'Y':
            speed = 6000
        elif axis == 'Z':
            speed = 1000
        else:
            print("Wrong axis provided.")
            return
        return speed
    

    def moveXY(self, x, y, speed=None):
        """
        Moves axes X and Y simultaneously. 
        Generates G-code for moving of the type: G0 X<value> Y<value> F<value>
        Passes G-code to 
        low_level_comm.writeAndWait() function (will wait for operation to complete)
        
        Inputs:
            x, y
                Final coordinate values in mm
            speed
                Moving speed for X an Y axes. Both will be moving with the same speed.
                Speed is measured in arbitrary units.
        """
        if speed == None:
            speed = self.getSpeed('X')
        full_cmd = 'G0 X' + str(x) + ' Y' + str(y) + ' F' + str(speed)
        try:
            self.writeAndWaitCartesian(full_cmd)
        except:
            print ("Movement failed. The following command was sent:")
            print (full_cmd)
            return


    def move(self, x=None, y=None, z=None, z_first=True, speed_xy=None, speed_z=None):
        """
        Move robot to a new position with given absolute coordinates.
        
            Inputs
                x, y, z
                    final coordinates to which to move the robot;
                    values in mm from homing position.
                    You can provide any of x, y or z, or all of them.
                    If both x and y provided, robot will move them simultaneously.
                z_first
                    if True and z value provided, will move Z coordinate first, 
                    then X and Y. Otherwise, will start from X and Y and then Z.
                    Default is True.
                speed_xy
                    Speed at which to move X and Y coordinates.
                    If not provided, library default values from arnie.speed will be used.
                speed_z
                    Speed at which to move Z coordinate.
                    If not provided, library default values from arnie.speed will be used.
        """
        
        if speed_xy == None:
            speed_xy = self.getSpeed('X')
        if speed_z == None:
            speed_z = self.getSpeed('Z')
        
        
        # Each of the functions attempting to move an axis to the coordinate. 
        # If something goes wrong, like coordinate not specified, command is ignored
        # and the next one is attempted.
        if z_first:
            if z is not None:
                self.moveAxis('Z', z, speed_z)
            # If both X and Y should be moved, I need to call moveXY(), one which would move
            # those axes simultaneously
            if x is not None and y is not None:
                self.moveXY(x=x, y=y, speed=speed_xy)
            elif x is not None:
                self.moveAxis('X', x, speed_xy)
            elif y is not None:
                self.moveAxis('Y', y, speed_xy)
        else:
            # If both X and Y should be moved, I need to call moveXY(), one which would move
            # those axes simultaneously
            if x is not None and y is not None:
                self.moveXY(x=x, y=y, speed=speed_xy)
            elif x is not None:
                self.moveAxis('X', x, speed_xy)
            elif y is not None:
                self.moveAxis('Y', y, speed_xy)
            if z is not None:
                self.moveAxis('Z', z, speed_z)
    
    
    def moveAxis(self, axis, dist, speed=None):
        axis = axis.upper()
        speed = self.getSpeed(axis)
        self.writeAndWaitCartesian('G0 '+axis+str(dist)+' F'+str(speed))
    

    def moveAxisDelta(self, axis, dist, speed=None):
        axis = axis.upper()
        speed = self.getSpeed(axis)
        
        pos = self.getPosition(axis=axis)
        new_pos = pos + dist
        self.writeAndWaitCartesian('G0 '+axis+str(new_pos)+' F'+str(speed))
    

    def getPosition(self, axis=None):
        msg = self.writeAndWaitCartesian("M114")
        msg_list = re.split(pattern=' ', string=msg)
        x_str = msg_list[0]
        y_str = msg_list[1]
        z_str = msg_list[2]
        x = float(re.split(pattern="\:", string=x_str)[1])
        y = float(re.split(pattern="\:", string=y_str)[1])
        z = float(re.split(pattern="\:", string=z_str)[1])
        try:
            axis=axis.upper()
        except:
            pass
        if axis == 'X':
            return x
        elif axis == 'Y':
            return y
        elif axis == 'Z':
            return z
        else:
            return x, y, z

        
    def moveDownUntilPress(self, step, threshold, z_max=180):
        self.tareAll()
        z = self.getPosition(axis='Z')
        z_init = z
        while ((self.getCombinedLoad()) < threshold) and (self.getPosition(axis='Z') < z_max):
            z += step
            self.moveAxis('Z', z)
        return self.getPosition(axis='Z')
        
    
    # TODO: include correction for a tip
    def moveToWell(self, rack_name, column, row, save_height=20):
        """
        Moves the robot to the specified well in the rack.
        Inputs:
            rack_name
                Name of the rack. Following names are allowed: 'samples', 'waste', 'tips', 'reagents'.
            column, row
                Position of the well using column and row number (not an x, y coordinates).
                For example, to get to the 96th well of a 96-well plate, specify column=11, row=7.
            save_height
                Height at which robot will not hit anything. 
                Specified relative to the rack top, which is obtained by the command rack.getZ()
                For example, value 20 (default) means that the robot will stop 20 mm above the rack.
        """
        # Current Z position
        z = self.getPosition(axis='Z')
        # Getting rack object
        r = self._getRackObjectByName(rack_name)
        # Rack top value
        z_top = r.getZ()
        z_safe = z_top - save_height
        # Checking whether I need to raise Z axis before movement
        if z > z_safe:
            self.moveAxis(axis='Z', dist=z_safe)
        # Obtaining well coordinates
        x, y = r.calcWellXY(column=column, row=row)
        # Moving towards the well
        self.move(x=x, y=y, z=z_safe, z_first=False)
        return self.getPosition()


# ==============================================================================
# Positioning routine

    
    def setPositioningParameters(self, step_list=[1, 0.2], z_increment=0.1, 
                                 z_retract=-1, z_max_travel=3, z_threshold=500):
        self._setSetting('stair_finding_step_list', step_list)
        self._setSetting('stair_finding_z_increment', z_increment)
        self._setSetting('stair_finding_z_retract_after_trigger', z_retract)
        self._setSetting('stair_finding_z_max_travel', z_max_travel)
        self._setSetting('stair_finding_z_load_threshold', z_threshold)
    
    
    def getPositioningParameters(self):
        step_list = self._getSetting('stair_finding_step_list')
        z_increment = self._getSetting('stair_finding_z_increment')
        z_retract = self._getSetting('stair_finding_z_retract_after_trigger')
        z_max_travel = self._getSetting('stair_finding_z_max_travel')
        z_threshold = self._getSetting('stair_finding_z_load_threshold')
        return step_list, z_increment, z_retract, z_max_travel, z_threshold


    def scanForStair(self, axis, step, direction, depth=5):
        """
        Detects abrupt drop in height (like a hole for a tube)
        """
        step_list, z_increment, z_retract, z_max_travel, z_threshold = self.getPositioningParameters()
        
        initial_z = self.getPosition(axis='Z')
        #initial_z = self.moveDownUntilPress(step=z_increment, threshold=z_threshold)
        z_trigger = initial_z
        while abs(initial_z - z_trigger) < z_max_travel:
            self.moveAxis('Z', initial_z)
            #self.moveAxisDelta('Z', z_retract)
            self.moveAxisDelta(axis, step*direction)
            z_trigger = self.moveDownUntilPress(step=z_increment, 
                            threshold=z_threshold, z_max=initial_z+depth)
            #print (z_trigger, abs(initial_z - z_trigger), z_max_travel)
        stair_coord = self.getPosition(axis=axis)
        return stair_coord

    
    def scanForStairFine(self, axis, direction):
        
        step_list, z_increment, z_retract, z_max_travel, z_threshold = self.getPositioningParameters()
        
        initial_z = self.moveDownUntilPress(step=z_increment, threshold=z_threshold)
        self.moveAxisDelta('Z', z_retract)
        
        for step in step_list:
            z_start = self.getPosition(axis="Z")
            coord = self.scanForStair(axis=axis, step=step, direction=direction)
            # Preparing to detect a stair with finer step
            # Moving up to initial height
            self.moveAxis('Z', z_start)
            # Moving one step back
            self.moveAxisDelta(axis, -step*direction)
        return coord
        
    
    # TODO: remove this function
    def findCenter(self, axis, distance, how='inner'):
        """
        Find an exact center of a hole. The pipette is expected to be approximately in
        the middle of the object.
        
        Inputs:
            axis
                'X' or 'Y', represents the axis for which to find a middle of the object
            distance
                Distance across the object, such as the diameter of the hole, or 
                measurement of the object
            how
                Values may be 'inner' or 'outer'. 'inner' is used in case if feature is a hole, such
                as a tube hole in a rack. 'outer' is used when one need to measure a solid object,
                such as a rack itself, or a capped tube.
                
        """
        if how == 'inner':
            direction = 1
        elif how == 'outer':
            direction = -1
        else:
            print ("Please specify a valid method for finding a center.")
            print ("If you want to find a center of a hole, please use how='inner' (default value) ")
            print ("If you want to find a center of a solid object, such as a rack, please use how='outer'")
            print ("You specified a value how=", how)
            return
        
        approx_center = self.getPosition(axis=axis)
        edge_1_approx = approx_center - distance/2.0
        edge_2_approx = approx_center + distance/2.0
        self.moveAxis(axis, edge_1_approx)
        edge_1 = self.scanForStairFine(axis, direction=direction)
        self.moveAxis(axis, edge_2_approx)
        edge_2 = self.scanForStairFine(axis, direction=-direction)
        center = (edge_1 + edge_2)/2.0
        return center


    def _findCenterXY(self, x1, x2, y1, y2, how):
        """
        Using coordinates of the object edge, find a center of this object
        """
        if how == 'inner':
            direction = 1
        elif how == 'well':
            direction = 1
        elif how == 'outer':
            direction = -1
        else:
            print ("Please specify a valid method for finding a center.")
            print ("If you want to find a center of a hole, please use how='inner' (default value) ")
            print ("If you want to find a center of a solid object, such as a rack, please use how='outer'")
            print ("You specified a value how=", how)
            return
            
        # Moving towards the rack
        self.moveAxis(axis='Z', dist=0) # Moving Z to 0 so I don't hit anything
        self.move(x1[0], x1[1], x1[2], z_first=False)
        x_edge_1 = self.scanForStairFine('X', direction=direction)
        self.moveAxisDelta('Z', lift_z)
        self.move(x2[0], x2[1], x2[2], z_first=False)
        x_edge_2 = self.scanForStairFine('X', direction=-direction)
        self.moveAxisDelta('Z', lift_z)
        self.move(y1[0], y1[1], y1[2], z_first=False)
        y_edge_1 = self.scanForStairFine('Y', direction=direction)
        self.moveAxisDelta('Z', lift_z)
        self.move(y2[0], y2[1], y2[2], z_first=False)
        y_edge_2 = self.scanForStairFine('Y', direction=-direction)
        
        x_center = (x_edge_1 + x_edge_2) / 2.0
        y_center = (y_edge_1 + y_edge_2) / 2.0
        
        return x_center, y_center
        
        
    def calibrateRack(self, rack):
        """
        Calibrates a selected rack. Possible rack values: 'samples', 'waste', 'tips', 'reagents'.
        """
        
        r = self._getRackObjectByName(rack_name=rack)
        
        # Obtaining calibration parameters
        (x1, x2, y1, y2, how)= r.getInitialCalibrationXY()
        lift_z = r.getCalibrationLiftZ()
        
        # Finding object center
        x_center, y_center = self._findCenterXY(x1, x2, y1, y2, how)
        
        # Depends on whether robot found a center of the rack, or a center of the well, 
        # the center of the rack is calculated and saved.
        if how == 'inner' or how == 'outer':
            r.setCenterXY(x=x_center, y=y_center)
        elif how == 'well':
            r.calcCenterFromWellXY(x=x_center, y=y_center)
        
        x_for_z_calibr, y_for_z_calibr = r.getZCalibrationXY(which='absolute')
        
        self.moveAxisDelta('Z', lift_z)
        self.move(x_for_z_calibr, y_for_z_calibr, x1[2], z_first=False)
        initial_z = self.getPosition(axis='Z')
        step_list, z_increment, z_retract, z_max_travel, z_threshold = self.getPositioningParameters()
        depth = 5
        z = self.moveDownUntilPress(step=z_increment, 
                            threshold=z_threshold, z_max=initial_z+depth)
        r.setZ(z)
        self.moveAxisDelta('Z', -5)
        
        return x_center, y_center, z

    
        
# ==============================================================================
# Settings storage and manipulations
        
    def loadData(self, path=None):
        if path is None:
            path=self.name+'.json'
        try:
            f = open(path, 'r')
            self.data = json.loads(f.read())
            f.close()
        except FileNotFoundError:
            self.data = {}
    
    
    def showData(self):
        return self.data
    
    
    def _getSetting(self, name):
        try:
            value = self.data[name]
        except:
            print ("Error: setting ", name, " is not specified.")
            print ("Use _setSetting('setting_name', value) to specify it.")
            print ("Alternatively, do self.data['setting_name']=value to set it temporary.")
            return
        return value
    
    def _setSetting(self, name, value):
        self.data[name] = value
        self.save()
    
    def save(self):
        f = open(self.name+'.json', 'w')
        f.write(json.dumps(self.data))
        f.close()
        
        

class rack():
    """
    Handles a rack info and functions
    """
    
    def __init__(self, name):
        self.name = name
        self.loadData()
        
        # Dictionary storing sample objects
        # {sample_object: (x_n, y_n)}
        # x_n, y_n - position (well) in the rack
        self.samples_dict = {}
    
    
    def _getSetting(self, name):
        try:
            value = self.data[name]
        except:
            print ("Error: setting ", name, " is not specified.")
            print ("Use _setSetting('setting_name', value) to specify it.")
            print ("Alternatively, do self.data['setting_name']=value to set it temporary.")
            return
        return value
    
    
    def _setSetting(self, name, value):
        self.data[name] = value
        self.save()
    
    
    def loadData(self, path=None):
        if path is None:
            path=self.name+'.json'
        try:
            f = open(path, 'r')
            self.data = json.loads(f.read())
            f.close()
        except FileNotFoundError:
            self.data = {}
    
    def save(self):
        f = open(self.name+'.json', 'w')
        f.write(json.dumps(self.data))
        f.close()
            
    def setSlot(self, slot_id):
        self._setSetting('slot_id', slot_id)
        
    def getSlot(self):
        self._getSetting('slot_id')
        
    def setCenterXY(self, x=None, y=None):
        """
        Sets rack center; x and y.
        """
        if x is not None:
            self._setSetting('center_x', x)
        if y is not None:
            self._setSetting('center_y', y)
            
    def getCenterXY(self):
        return self._getSetting('center_x'), self._getSetting('center_y')
        
    def setCalibrationZ(self, z):
        """
        Sets absolute Z value at which calibration starts for the rack
        """
        self._setSetting('calibration_Z', z)
        
    def getCalibrationZ(self):
        """
        Returns absolute Z value at which calibration shall start
        """
        return self._getSetting('calibration_Z')
        
    def setZ(self, z):
        """
        Sets the value at which pipette without a tip touches the top of the rack,
        detected by the load cells.
        """
        self._setSetting('detected_z', z)
        
    def getZ(self):
        """
        Returns Z value at which the pipette without a tip would touch the rack, triggering load cells.
        """
        return self._getSetting('detected_z')
        
    def setRackSize(self, x, y, z):
        """
        Specifies rack dimensions in mm. Z value is the height of the rack from the floor.
        """
        self._setSetting('max_x', x)
        self._setSetting('max_y', y)
        self._setSetting('max_z', z)
        
    def getRackSize(self):
        """
        Returns rack dimensions in mm.
        """
        return self._getSetting('max_x'), self._getSetting('max_y'), self._getSetting('max_z')
    
    
    def setCalibrationStyle(self, style, well_x=0, well_y=0):
        self._setSetting('calibration_style', style)
        self._setSetting('x_well_to_calibrate', well_x)
        self._setSetting('y_well_to_calibrate', well_y)
    
    
    def getCalibrationStyle(self, well=None):
        if well is None:
            return self._getSetting('calibration_style')
        else:
            calib_style = self._getSetting('calibration_style')
            x_well = self._getSetting('x_well_to_calibrate')
            y_well = self._getSetting('y_well_to_calibrate')
            return calib_style, x_well, y_well
            
    
    
    def setWells(self, wells_x, wells_y, x_dist_center_to_well_00, y_dist_center_to_well_00, well_diam,
                 dist_between_cols, dist_between_rows):
        """
        Specifies number of wells in the rack and their position relative to the center
        """
        self._setSetting('wells_x', wells_x)
        self._setSetting('wells_y', wells_y)
        self._setSetting('x_dist_center_to_well_00', x_dist_center_to_well_00)
        self._setSetting('y_dist_center_to_well_00', y_dist_center_to_well_00)
        self._setSetting('well_diam', well_diam)
        self._setSetting('dist_between_cols', dist_between_cols)
        self._setSetting('dist_between_rows', dist_between_rows)
    
    def getWellsParams(self):
        x = self._getSetting('x_dist_center_to_well_00')
        y = self._getSetting('y_dist_center_to_well_00')
        columns = self._getSetting('wells_x')
        rows = self._getSetting('wells_y')
        well_diam = self._getSetting('well_diam')
        dist_between_cols = self._getSetting('dist_between_cols')
        dist_between_rows = self._getSetting('dist_between_rows')
        return x, y, columns, rows, well_diam, dist_between_cols, dist_between_rows
    
    def getWellDiameter(self):
        return self._getSetting('well_diam')
    
    
    def calcWellsXY(self):
        x_rack_center, y_rack_center = self.getCenterXY()
        x_well_0_rel, y_well_0_rel, columns, rows, well_diam, dist_between_cols, dist_between_rows = self.getWellsParams()
        
        x_well_0 = x_rack_center - x_well_0_rel
        y_well_0 = y_rack_center - y_well_0_rel
        
        coord_list = []
        coord_added_x = 0
        
        for i in range(columns):
            coord_i = x_well_0 + coord_added_x
            coord_added_x += dist_between_cols
            
            coord_list_y = []
            coord_added_y = 0
            for j in range(rows):
                coord_j = y_well_0 + coord_added_y
                coord_list_y.append((coord_i, coord_j))
                coord_added_y += dist_between_rows
            coord_list.append(coord_list_y)
        
        return coord_list
    
    
    def calcWellXY(self, column, row):
        coord_list = self.calcWellsXY()
        return coord_list[column][row][0], coord_list[column][row][1]
    
    
    def getInitialCalibrationXY(self):
        style = self.getCalibrationStyle()
        if style=='outer' or style == 'inner':
            # This case happens if the rack is to be calibrated from outside (like samples rack), or 
            # using a large hole inside (like the tip rack or waste rack).
            x, y = self.getCenterXY() # X and Y coordinates of the center of the rack
            # X, Y, Z dimensions of the rack
            max_x, max_y, max_z = self.getRackSize()
            # Calculating edges of the rack
            x_edge_1 = x - max_x/2.0
            x_edge_2 = x + max_x/2.0
            y_edge_1 = y - max_y/2.0
            y_edge_2 = y + max_y/2.0
        elif style=='well':
            style, column, row = self.getCalibrationStyle(well=True)
            x, y = self.calcWellXY(column, row)
            well_diam = self.getWellDiameter()
            # Calculating edges of the well that will be used for calibration
            x_edge_1 = x - well_diam/2.0
            x_edge_2 = x + well_diam/2.0
            y_edge_1 = y - well_diam/2.0
            y_edge_2 = y + well_diam/2.0
        else:
            print("Provided calibration style is not supported.")
            print("Please use 'outer', 'inner' or 'well' styles.")
            print("Current provided style is: ", style)
        # Z coordinate at which calibration is started
        z = self.getCalibrationZ()
        # Formatting the calibration points coordinates. All in the form of (x, y, z)
        p1 = (x_edge_1, y, z)
        p2 = (x_edge_2, y, z)
        p3 = (x, y_edge_1, z)
        p4 = (x, y_edge_2, z)
        return p1, p2, p3, p4, style
        
    def calcCenterFromWellXY(self, x, y, column=None, row=None):
        if column is None or row is None:
            style, column, row = self.getCalibrationStyle(well=True)
        
        x_well_0_rel, y_well_0_rel, columns, rows, well_diam, dist_between_cols, dist_between_rows = self.getWellsParams()
        
        x_cntr_abs = x - dist_between_cols * column + x_well_0_rel
        y_cntr_abs = y - dist_between_rows * row + y_well_0_rel
        
        self.setCenterXY(x=x_cntr_abs, y=y_cntr_abs)

    def setCalibrationLiftZ(self, z):
        """
        Height for which to lift Z axis during calibration
        """
        self._setSetting('calibration_lift_z', z)
    
    def getCalibrationLiftZ(self):
        """
        Returns the height at which to leave the pipette during calibration (so it does not hit anything)
        """
        return self._getSetting('calibration_lift_z')
        
    def setZCalibrationXY(self, x=0, y=0):
        """
        Defines coordinates (relative to the rack center) at which to perform calibration of the rack height
        """
            
        self._setSetting('x_coord_for_z_calibration', x)
        self._setSetting('y_coord_for_z_calibration', y)
    
    def getZCalibrationXY(self, which='relative'):
        """
        Returns x and y coordinates of the point at which Z of the rack needs to be calibrated.
        Coordinates are relative to the center of the rack.
        """
        
        x_rel = self._getSetting('x_coord_for_z_calibration')
        y_rel = self._getSetting('y_coord_for_z_calibration')
        
        if which == 'relative':
            return x_rel, y_rel
        elif which == 'absolute':
            x_cntr, y_cntr = self.getCenterXY()
            x_abs = x_cntr + x_rel
            y_abs = y_cntr + y_rel
            return x_abs, y_abs
        else:
            print ('Please specify type of the coordinate you need.')
            print ("which='relative' will give coordinates relative to the rack center;")
            print ("which='absolute' will give absolute coordinates.")
            return
        