import serial
import sys
import json


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
    
    
class data():
    """
    Handles data input and output
    """
    
    def __init__(self, name):
        self.name = name
        self.loadData()
    
    
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
        

    def loadData(self, path=None):
        if path is None:
            path=self.name+'.json'
        try:
            f = open(path, 'r')
            self.data = json.loads(f.read())
            f.close()
        except FileNotFoundError:
            self.data = {}