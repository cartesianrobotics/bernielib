import serial
import time
import re
import logging
import sys
import json


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
        
        self.cartesian_port = serial.Serial(cartesian_port_name, BAUDRATE, timeout=TIMEOUT)
        self.pipette_port = serial.Serial(pipette_port_name, BAUDRATE, timeout=TIMEOUT)
        self.misc_port = serial.Serial(misc_port_name, BAUDRATE, timeout=TIMEOUT)
    
    
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
        
    
    def pipetteUnlock(self):
        self.writeAndWaitPipette('$X')
    
    
    def pipetteMove(self, dist):
        dist = dist * -1.0
        self.writeAndWaitPipette('G0 X'+str(dist))
        
    
    def pipetteServoUp(self):
        self.writeAndWaitPipette('M3 S90')
        
    
    def pipetteServoDown(self):
        self.writeAndWaitPipette('M5')
    
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
        self.data['magnets_away_angle'] = angle
        self.save()
    
    
    def setMagnetsNearTubeAngle(self, angle):
        self.data['magnets_near_tube_angle'] = angle
        self.save()
    
    
    def getMagnetsAwayAngle(self):
        try: 
            return self.data['magnets_away_angle']
        except:
            return 40
    
    def getMagnetsNearTubeAngle(self):
        try:
            return self.data['magnets_near_tube_angle']
        except:
            return 90
    
    
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
        if axis is None:
            self.writeAndWaitCartesian('G28 Z')
            self.writeAndWaitCartesian('G28 X')
            self.writeAndWaitCartesian('G28 Y')
        else:
            axis=axis.upper()
            self.writeAndWaitCartesian('G28 '+axis)
    
    
    def moveAxis(self, axis, dist, speed=None):
        axis=axis.upper()
        if speed is None:
            if axis == 'X' or axis == 'Y':
                speed = 6000
            elif axis == 'Z':
                speed = 1000
            else:
                print("Wrong axis provided.")
                return
        self.writeAndWaitCartesian('G0 '+axis+str(dist)+' F'+str(speed))
        

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

        
    def moveDownUntilPress(self, step, threshold):
        self.tareAll()
        z = self.getPosition(axis='Z')
        while (self.getCombinedLoad()) < threshold:
            z += step
            self.moveAxis('Z', z)
        return self.getPosition(axis='Z')
        
        
        
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
    
    
    def save(self):
        f = open(self.name+'.json', 'w')
        f.write(json.dumps(self.data))
        f.close()