import serial
import serial.tools.list_ports
import convert as con
import save
import math
from statistics import mean
from forceconversion import FC
from datetime import datetime
import time



class Sensor:
    """This class covers all the used functions of the sensor"""
    def __init__(self, *args, **kwargs):
        
        # self.usb is a list of all connected usb ports. 
        self.usb = []
        for info in serial.tools.list_ports.comports():
            port, desc, hwid = info
            self.usb.append(port)
        print(port)
        print("This is USB list",self.usb)      
        
        # iterating through self.usb to find the one the sensor is connected to.
        # that one will then be deleted from the list and the list will be used by Main.py to connect the motorstages
        for i in range(len(self.usb)):
            self.sens = serial.Serial( 
                port= self.usb[i],             # chooses the port to which you want to connect,
                                               #  if you don't know to which port you want to connect
                                               #  run py -m serial.tools.list_ports from your console,
                                               #  this will give you a list of available ports. 
                baudrate=250000,           # sets the speed of symbol transfer (same as byterate),
                                               #  specified in ASCII command sheet, do not change
                parity=serial.PARITY_NONE,   
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.2, # was 0.2
                write_timeout=3
                )
            connection = self.connection_check()
            if connection:
                print("connected the sensor at", self.usb[i])
                del self.usb[i]
                break          
        
        # read out the buffer of the sensor
        self.sens.write(b'/stop\r\n')
        print(self.sens)
        print('buffer: ' )
        beforereading = time.time()
        s = self.sens.readline()
        afterreading = time.time()
        print('time for reading: ', afterreading-beforereading)
        print(s)
        while s != b'':
            beforereading = time.time()               
            s = self.sens.readline()
            afterreading = time.time()
            print('time for reading: ', afterreading-beforereading)
            print(s)
        # set the format in which the sensor sends information to default,
        # sometimes the sensor is confused and convert won't work
        self.sens.write(b"/setConfig Tformat TformatDef \r\n")
        # self.sens.write(b"/setConfig Tformat 4 \r\n")
        # self.sens.write(b"/setConfig Tformat 79 \r\n")
        # print(self.sens.readline())           
        self.channel = 2    # the default channel is 2(bend)
        self.configdict = self.make_configdict() # dictionary containing the configuration data from the sensor
        print('configdict:', self.configdict)
        self.emptystreamdict = self.make_emptystreamdict() # empty streamdict, to which data can be appended
        self.forcelist = self.make_forcelist() # makes a forcelist from the emptystreamdict
        self.avgdict = self.make_avgdict() # dictionary containing the average and samplerates of the sensor

        self.conversionfactor = 1/100 # will be changed after calibration
        self.beamdict = save.read_yamldict('beams.yaml') # dictionary of already calibrated beams
        self.current_beam = 'no beam selected' # will be set to the beam selected in the beamcalibration
        self.timelist = [] # a list to which the timestamps can be appended
        self.timereal = [] # a list to which real time of reading can be added

        self.now = datetime.now()

   
    def connection_check(self):
        """Sends and evaluates an identity request,
        to make sure the right device is connected"""
        self.sens.write(b'/idn?\r\n')            
        ans = self.sens.readline()
        opt_ans = b'idn Philtec DMS serial 2421 fwVer 2.807 cs d1a\n'
        if ans == opt_ans: 
            print("Congratulations! You managed to connect to the right device.")
            return True
        elif ans == b"":
            print(" The device is not responding, check whether you connected it to a power source")
            return False
        else:
            print("Something seems to be wrong, check wheter you have the right device plugged in")
            return True

    def make_metadata(self):
        """ makes a list out of several metadata lists. This list is passed to the save_with_metadata function
        Aurelie: I added a few exceptions because sometimes it would not save the data properly"""
        time = ['data and time', self.now.strftime("%d/%m/%Y %H:%M:%S")]
        beam = ['beam',self.current_beam]
        try: 
            temp = ['mean temperature', mean(self.emptystreamdict['temp'])]
        except:
            temp = ['mean temperature']
        speed = ['samplerate', str(round((2**self.configdict['avg']*self.configdict['sampleClkPer'])**(-1),2))+' samples/s']
        average = ['average over x measurements', 2**self.configdict['avg']]
        try:
            lintensity = ['mean lightintensity', mean(self.emptystreamdict['snr'])]   
        except:
            lintensity = ['mean lightintensity']
        tare = ['tare distace', FC.tare]
        if self.channel == 1:
            sensor = ['Sensor', 'straight']     
        elif self.channel == 2:
            sensor = ['Sensor', 'bend']
        else: # better to save it in two seperate csv
            sensor = ['Sensor', 'straight']
            sensor2 = ['Sensor', 'bend']
            lintensity2 = ['mean lightintensity', mean(self.emptystreamdict['snr2'])]
            lintensity = ['mean lightintensity', mean(self.emptystreamdict['snr'])]
        self.metadata = [time,sensor, beam, temp, lintensity,speed, average,tare] # implement both
        return self.metadata

    def make_forcelist(self):
        """calculates the applied force in mN based on the distance in the stramdict and a conversionfactor"""
        self.forcelist=[]
        FC.calc_uomconversion()
        for i in range(len(self.emptystreamdict['distn'])):
            self.tareddist = self.emptystreamdict['distn'][i]-FC.tare
            self.forcelist.append(self.tareddist*FC.uomconvfact*self.conversionfactor)
        return self.forcelist

    def make_data(self):
        """makes a streamdict of relevant data (time, distance, force). This streamdict is passed to the save_with_metadata function"""
        self.uom = str(sens.configdict['uom'])
        self.data = {}
        self.data['time in s'] = self.timelist
        self.data['real time in s'] = self.timereal
        self.data['dist in '+self.uom] = []
        for i in self.emptystreamdict['distn']:
            self.data["dist in "+self.uom].append(i-FC.tare)
        self.forcelist = self.make_forcelist()
        
        self.data['force in mN']= self.forcelist
        return self.data


    def make_configdict(self):
        """makes a dictionary of the sensors current configuration settings

        The dictionary includes in this sequence: avg, avgDef, calTable, uom, 
        gain, Dpeak, TformatDef, Tformat, fwVer (firmware Version), serial, 
        sign, bps, snrMax, calTableMax, analog1, analog2, cmdLenMax, bpsRange,
        sampleClkPer, RCDCode, HWCode, Tchselect, calTable2, gain2, Dpeak2, sign2, cs.
        The channel setting will be ignored """ 
        self.sens.write(b'/getConfig\r\n')
        ans = self.sens.readline()
        print("GetConfig", ans)
        self.configdict = con.make_dict(ans,channel=0)
        #self.configdict = con.make_dict(self.sens.readline(),channel=0)
        print("Configdict", self.configdict)
        FC.uom = self.configdict['uom']
        return self.configdict
    
    def make_calibdict(self):
        self.sens.write(b'/getCal\r\n')
        rawans = self.sens.readline()
        print(rawans)
       # self.calibdict = con.make_dict(self.sens.readline(),channel=0)
        self.calibdict = con.make_dict(rawans,channel=0)
        self.calibdata = self.calibdict['points'][1:]
        print('calibdata: ,')
        self.distance =['distance']
        self.signal = ['distn']
        self.snr = ['snr']
        self.csvdata = []
        for i in range(len(self.calibdata),3):
            print(i)
            self.distance.append(self.calibdata[i])
            self.signal.append(self.calibdata[i+1])
            self.snr.append(self.calibdata[i+2])
            # self.csvdata.append(self.calibdata[i:i+2])
        self.csvdata = [self.distance,self.signal,self.snr]
        save.lists_to_csv(self.csvdata,'calibtable.csv')        
        return self.calibdict

    def make_emptystreamdict(self):
        """makes a dictionary of the sensors current configuration settings
        The dictionary normally includes in this sequence: temp, distn, snr, distn, 
        distf, refp, distn2, snr2, distn2, distf2, refp2, cs
        all kwargs containing 2 will be changed or omitted by apply channel in convert"""
        self.sens.write(b'/T\r\n')
        ans = self.sens.readline()
        print("ans", ans)
        self.emptystreamdict = con.make_streamdict(self.sens.readline(),self.channel)
        #self.emptystreamdict = con.make_streamdict(self.sens.readline(),self.channel)
        for i in self.emptystreamdict:
            self.emptystreamdict[i]=[]
        if len(self.emptystreamdict) == 1: # happens when there was still a stop flag to be read out
            self.emptystreamdict = con.make_streamdict(self.sens.readline(),self.channel)
            for i in self.emptystreamdict:
                self.emptystreamdict[i]=[]
        return self.emptystreamdict

    def make_avgdict(self):
        """makes a dictionary linking the samplerate value to the according
        avg value starting from 12 going down to 1. The average is the kw, 
        the sampelrate the arg"""
        avg = [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        self.avgdict = {}
        for i in avg:
            item = round((2**i*self.configdict['sampleClkPer'])**(-1),2)
            self.avgdict[item] = 2**i
        print(self.avgdict)
        return self.avgdict

    def set_temp(self, wantTemp):
        """sets the wanted temperature of the sensor to wantTemp"""
        self.sens.write(b'/setConfig setTemp ' + wantTemp + b'\r\n') 
        print(self.sens.readline()) 

    def get_temp(self):
        """gets the current temperature of the sensor and returns it as a string"""
        # buffer = self.sens.readlines()
        # print('buffer: '+ str(buffer))
        self.sens.write(b'/T\r\n')
        rawans = self.sens.readline()
        #print(rawans)
        ans = con.make_stringdict(rawans,self.channel)
        self.temp = ans['temp']    
        return self.temp  

    def make_targetdict(self): # this is not really used 
        """makes a dictionary from the taget answer of the sensor, all values are strings"""
        self.sens.write(b'/T\r\n')
        rawans = self.sens.readline()
        self.targetdict = con.make_stringdict(rawans,self.channel)
        return self.targetdict

    def set_lightpower(self, wantLightpower):
        """sets the wanted light intensity of the sensor to wantLightpower"""
        if self.channel == 1:
            self.sens.write(b'/setConfig gain ' + wantLightpower + b'\r\n')
        elif self.channel == 2:
            self.sens.write(b'/setConfig gain2 ' + wantLightpower + b'\r\n')
        print(self.sens.readline()) 

    def get_lightpower(self):
        """gets the current lightpower of the via channel selected sensor 
        and returns it as a string."""
        self.sens.write(b'/T\r\n')
        rawans = self.sens.readline()
        #print(rawans)
        ans = con.make_stringdict(rawans,self.channel)
        power = ans['snr']    # still need to implement both channels 
        return power
    
    def set_samplerate(self, avg):
        """sets the samplerate of the sensor to the selected samplerate"""
        self.avgvalue = str(int(math.log(avg,2))).encode()
        b = b'/setConfig avg '+ self.avgvalue + b'\r\n'
        print(b)
        self.sens.write(b)
        print(self.sens.readline())

    def set_uom(self,uom):
        """sets the unit of measure to uom"""
        uom = uom.encode()
        self.sens.write(b'/setConfig uom ' + uom +b'\r\n' )
        print(self.sens.readline())

    def start_stream(self):
        """starts a datastream and reads and prints the header"""
        self.sens.write(b'/T stream ascii\r\n')
        self.header = self.sens.readline()
        #print(self.header)

    def stop_stream(self, streamdict):
        """stops a datastream and reads out the buffer"""
        self.sens.write(b'/stop\r\n')
        self.buffer = self.sens.readlines()
        print(self.buffer)
        try:
            con.append_to_streamdict(streamdict, self.buffer,sens.channel,omitted=0)
        except:
            print('There was some problem with reading out the buffer')
        # save.streamdict_to_csv(streamdict)


sens = Sensor()     
