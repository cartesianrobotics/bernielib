import serial
import sys
import json
import os


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
        self.factory_default_path = './factory_default/' + self.name + '.json'
        self.loadData()
    
    
    def _getSetting(self, name):
        try:
            value = self.data[name]
        except:
            try:
                # If a setting was not find in the local settings, trying to 
                # get them from the factory default
                factory_default_data = self.loadFactoryDefault()
                value = factory_default_data[name]
                # Addting the missing setting to the local settings
                self._setSetting(name, value)
            except:
                print ("Error: setting ", name, " is not specified.")
                print ("Use _setSetting('setting_name', value) to specify it.")
                print ("Alternatively, do self.data['setting_name']=value to set it temporary.")
                return
        return value
        
    def _settingPresent(self, name):
        try:
            value = self.data[name]
            present = True
        except:
            present = False
        return present

    
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
            self.data = self.loadFactoryDefault()
            # Copying factory defaults into the local settings
            self.save()
    
    
    def loadFactoryDefault(self):
        try:
            f = open(self.factory_default_path, 'r')
            factory_default_data = json.loads(f.read())
            f.close()
        except FileNotFoundError:
            factory_default_data = {}
        return factory_default_data
    
    
    def purge(self):
        """
        Attention! Do not run unless you know what you are doing.
        Removes all data for the object, both on hard drive and memory.
        """
        try:
            os.remove(self.name+'.json')
        except:
            pass
        self.data = {}