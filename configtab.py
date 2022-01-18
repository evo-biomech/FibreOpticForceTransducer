import tkinter as tk
from tkinter import ttk
from sensor import Sensor
from sensor import sens
from threading import Thread
import math
import time


class ConfigTab (tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.togglevar = 0 # used to assign two alternating functions to the advbtn
        self.configframe = tk.Frame(self)
        self.configframe.pack()
        # left half

        self.channellbl = tk.Label(self.configframe, text='sensor')
        self.channelentry = ttk.Combobox(self.configframe)
        self.channelentry['values'] = ('straight (ch1)','bend (ch2)')
        self.channelentry.current(1)
        self.channelset = tk.Button(self.configframe, text ='set', command=self.set_channel)
        
        

        self.avglbl = tk.Label(self.configframe, text='frequence of measurements in samples/s')
        #self.avgx = tk.Label(self.configframe,text='x = ')
        self.avgselect = ttk.Combobox(self.configframe)
        self.avgvalues = list(sens.avgdict)            
        self.avgselect['values'] = self.avgvalues
        
        
        # gets the current avg value from sens.configdict and displays it in the GUI
        for i in range(len(self.avgvalues)):
            if sens.configdict['avg'] == int(math.log(list(sens.avgdict.values())[i],2)):
                self.crntspd = i
        self.avgselect.current(self.crntspd)   #sets it to current value
        self.avgset = tk.Button(self.configframe, text='set',command=self.setsamplerate)
        self.speedtxt = 'averaged over ' + str(2**sens.configdict['avg'])+ ' measurements'
        self.speedlbl = tk.Label(self.configframe, text= self.speedtxt)  

        self.advbtn = tk.Button(self.configframe, text='advanced Settings', command=self.make_advset)        
        self.advsetframe = AdvancedSettings(self.configframe)

        #placing widgets
        for i in [0,1,3,4]:
            self.columnconfigure(i, pad=3)
        
        self.columnconfigure(2, pad=5)

        self.channellbl.grid(row=0, column=0)
        self.channelentry.grid(row=1,column=0)
        self.channelset.grid(row=1,column=1)
        
        self.avglbl.grid(row=0,column=3)
        self.avgselect.grid(row=1,column=3)
        self.avgset.grid(row=1,column=4)
        self.speedlbl.grid(row=2,column=3) 

        self.advbtn.grid(row=3,column=0, columnspan=5)
        
    
    def make_advset(self):
        if self.togglevar == 0: 
            self.advsetframe.running = True
            self.advsetframe.get_temp_and_light() # starts the thread updating the light and temp label
            self.advsetframe.grid(row=4,column=0,columnspan=5)
            self.togglevar = 1
        else:
            self.advsetframe.running = False
            self.advsetframe.grid_forget()
            self.togglevar = 0

    def set_channel(self):
        """updates the channel attribute of sens to the entry of the choicebox"""
        if self.channelentry.get() == 'both':
            sens.channel = 0 # start of implementing both sensors
        elif self.channelentry.get() == 'straight (ch1)':
            sens.channel = 1
        else:
            sens.channel = 2

    def setsamplerate(self):
        """sends the avg value corresponding to the average to the sensor"""
        print("frequency value to set: ", self.avgselect.get())
        self.average = sens.avgdict[float(self.avgselect.get())]        
        # print(self.average)
        if self.togglevar == 1: # if advsetframe is open and the thread is running
            self.advsetframe.running = False # stop thread
            self.advsetframe.templightthread.join() # needed for the thread to finish, while it is running sending commands will confuse the sensor
            sens.set_samplerate(self.average)
            sens.conficdict = sens.make_configdict()
            self.advsetframe.running = True
            self.advsetframe.get_temp_and_light() # start thread again
        else:
            sens.set_samplerate(self.average)
        SensConnect = sens.connection_check()
	    #print(SensConnect)
        self.speedtxt = 'averaged over ' + str(2**sens.configdict['avg'])+ ' measurements'
        self.speedlbl.configure(text=self.speedtxt)
        print("sensor sample rate: ", sens.avgdict)
                       
    

class AdvancedSettings (ttk.Frame):
    def __init__(self,parent):
        ttk.Frame.__init__(self,parent)
        self.advsetframe = ttk.Labelframe(self, text='advanced Settings') 
        self.advsetframe.pack()
        self.uomlbl = tk.Label(self.advsetframe, text='unit of measure')
        self.uomchoice = ttk.Combobox(self.advsetframe)
        self.uom = ['um','mm','nm','mI']
        self.uomchoice['values'] = self.uom

        # find the current unit of measure (uom)
        for i in range(len(self.uom)):
            if sens.configdict['uom'] == self.uom[i]:
                self.crntuom = i

        self.uomchoice.current(self.crntuom) # sets it to the current value
        self.uomset = tk.Button(self.advsetframe, text='set',command=self.setuom)

        self.templbl = tk.Label(self.advsetframe, text='Temperature setting')
        self.tempentry = tk.Entry(self.advsetframe,width=10)
        self.tempset = tk.Button(self.advsetframe, text='set Temp', command = self.set_temp)
        self.actualtemp = tk.Label(self.advsetframe,text = 'current temperature: ')
       
        self.lightlbl = tk.Label(self.advsetframe, text='light intensity')
        self.lightentry = tk.Entry(self.advsetframe, width=10)
        self.setintensity = tk.Button(self.advsetframe, text='set intensity',command=self.set_light)
        self.maxlightlbl = tk.Label(self.advsetframe, text='max allowed recieved power: '+ str(sens.configdict['snrMax'])) 
        self.crntlightlbl = tk.Label(self.advsetframe, text='amount of light recieved: ')

        self.uomlbl.grid(row=0,column=0)
        self.uomchoice.grid(row=1,column=0)
        self.uomset.grid(row=1,column=1)
        self.templbl.grid(row=2 , column=0)
        self.actualtemp.grid(row=3,column=0)
        self.tempentry.grid(row=4,column=0)
        self.tempset.grid(row=4,column=1)
        
        self.lightlbl.grid(row=0,column=3)
        self.maxlightlbl.grid(row=1,column=3)
        self.crntlightlbl.grid(row=2,column=3)
        self.lightentry.grid(row=3,column=3)
        self.setintensity.grid(row=3,column=4) 

        self.running = False # makes sure thread is not running until advbtn is pressed

    def build_second_light(self):#still needs to be implemented
        """will only be used when both channels are selected"""
        self.crnlightlbl2 = tk.Label(self.advsetframe, text = 'amount of light ')


    def setuom(self):
        """ sends the entered uom to the sensor"""
        self.running=False
        self.templightthread.join() # waites for the thread to finish
        sens.set_uom(uom=self.uomchoice.get())   
        sens.configdict = sens.make_configdict()
        self.running=True
        self.get_temp_and_light()
      
    def set_temp(self):
        """sends the entered temperature to the sensor"""
        wantTemp = self.tempentry.get().encode()
        self.running=False
        self.templightthread.join() #waites for the thread to finish
        print(wantTemp)
        sens.set_temp(wantTemp) 
        self.running=True  
        self.get_temp_and_light()
       

    def get_temp_and_light(self):
        """continously updates the actualtemp label and the current lightintensity"""
        def run():  
            print("configthread started")
            i = 0
            while self.running:
                i = i+1
                self.targetdict = Sensor.make_targetdict(sens)
                # print(self.targetdict)
                self.temp = self.targetdict['temp']
                #self.power = self.targetdict['snr']
                if sens.channel == 0:
                    self.power = self.targetdict['snr']
                    self.power2 = self.targetdict['snr2']
                else:
                    self.power = self.targetdict['snr']
                   
                self.actualtemp.configure(text='current Temperature: '+ self.temp)
                self.crntlightlbl.configure(text='amount of light recieved: '+ self.power)
                time.sleep(0.7) #this is necessary for the thread to finish when self.running = False. I don't know why
                                # if a thread error occurs try setting this value higher
            print("configthread stopped after ",i," iterations")
        self.templightthread = Thread(target=run)
        self.templightthread.start()

    def set_light(self):
        """sends the entered light value to the sensor"""
        wantlight = self.lightentry.get().encode()
        self.running = False
        self.templightthread.join() 
        sens.set_lightpower(wantlight)
        sens.configdict = sens.make_configdict()
        self.running=True
        self.get_temp_and_light()
       

    

if __name__ == "__main__":
   
    root = tk.Tk()
    app = ConfigTab(root)
    app.pack()
    root.mainloop()