import tkinter as tk
from tkinter import ttk
from threading import Thread
import convert as con
from sensor import sens
import save 
from forceconversion import FC
import time

class dFrame(ttk.Labelframe):
    """gives the possibility to enable and disable a frame"""
    def enable(self, state='!disabled'):

        def cstate(widget):
            widget.state((state,))
            # Is this widget a container?
            if widget.winfo_children:
                # It's a container, so iterate through its children
                for w in widget.winfo_children():
                    # change its state
                    w.state((state,))
                    # and then recurse to process ITS children
                    cstate(w)

        cstate(self)

    def disable(self):
        self.enable('disabled')

class CalibWindow(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        
        v = tk.IntVar() # used for proper functioning of the radiobuttons     
        self.chooseframe = dFrame(self, text='choose beam')
        self.choosebox = ttk.Combobox(self.chooseframe)
        self.choosebox['values']=list(sens.beamdict)
        self.forcelengthlbl = ttk.Label(self.chooseframe,text='distance to force application (mm): ')
        self.measurelengthlbl = ttk.Label(self.chooseframe,text='distance to measurement point (mm)')
        self.forcelengthentry = ttk.Entry(self.chooseframe)
        self.measurelengthentry = ttk.Entry(self.chooseframe)
        self.setchoicebtn = ttk.Button(self.chooseframe,text='apply',command=self.calculate)
        self.tarelbl = ttk.Label(self.chooseframe,text='distance to beam')
        self.taredistlbl = ttk.Label(self.chooseframe,text='--')
        self.tarebtn = ttk.Button(self.chooseframe,text='tare',command=self.tare)
        self.undotarebtn = ttk.Button(self.chooseframe, text="undo tare",command=self.undo_tare)
        self.updatetare = False # controls the thread to update the taredistlbl of the beamcalibframe
        self.chooseframe.disable()

        self.calibframe = dFrame(self, text='new calibration')
        self.knownEmodul = ttk.Radiobutton(self.calibframe,text='known Emodul',variable = v,value=1,command=self.make_emodulcalib)
        self.unknownEmodul = ttk.Radiobutton(self.calibframe,text='unknown Emodul',variable=v,value=2,command=self.make_weightcalib)
        self.calibframe.disable()

        self.choosebtn = ttk.Radiobutton(self,text='choose beam',variable=v,value=3,command=self.enablechooseframe)
        self.calibbtn = ttk.Radiobutton(self,text='new calibration',variable=v,value=4,command=self.enablecalibframe)

        self.weightcalib = WeigthCalib(self.calibframe)
        self.emodulcalib = EmodulCalib(self.calibframe)


        #place widgets in startframe
        self.choosebtn.grid(row=0,column=0)
        self.calibbtn.grid(row=0,column=1)
        self.chooseframe.grid(row=1,column=0)
        self.calibframe.grid(row=1,column=1)

        #place widgets in chooseframe
        self.choosebox.grid(row=0,column=0)
        self.forcelengthlbl.grid(row=1,column=0)
        self.forcelengthentry.grid(row=1,column=1)
        self.measurelengthlbl.grid(row=2,column=0)
        self.measurelengthentry.grid(row=2,column=1)
        self.tarelbl.grid(row=3,column=0)
        self.taredistlbl.grid(row=3,column=1)
        self.tarebtn.grid(row=3,column=2)
        self.undotarebtn.grid(row=4,column=2)
        self.setchoicebtn.grid(row=5,column=0,columnspan=3)


        # place widgets in calibframe
        self.knownEmodul.grid(row=0,column=0)
        self.unknownEmodul.grid(row=0,column=1)
    
    def tare(self):
        """passes the tare distance to forceconversion"""
        print(self.taredistlbl.cget('text'))
        self.tared = float(self.taredistlbl.cget('text'))
        FC.tare = self.tared
        self.updatetare=False

    def undo_tare(self):
        """restarts the thread to update the tarelbl"""
        self.updatetare = True
        self.update_distlbl()

    def update_distlbl(self):
        """ constantly updates the distance value"""
        def run():
            print("chooseframe thread started")
            sens.sens.write(b'/T \r\n') 
            ans = sens.sens.readline()
            sens.sens.write(b'/getConfig\r\n')
            ans = sens.sens.readline()
            print('configdict:', ans)
            # time_0 = time.time()
            while self.updatetare:
                print("Hello")
                sens.sens.write(b'/T \r\n')                
                self.target = con.make_dict(sens.sens.readline(),sens.channel)
                print("target:", self.target)
                self.distance = self.target['distn'].astype(float)
                print("distance:", self.distance)
                # print(time.time()-time_0)
                # time_0 = time.time()
                # self.distance = sens.emptystreamdict['distn2'][-1]
                
                self.taredistlbl.configure(text=self.distance)
                # print(self.distance)
            print("chooseframe thread stopped")
        self.thread = Thread(target = run) 
        self.thread.start() 
        print("thread started")
        #sens.sens.write(b'/getConfig\r\n')
        #ans = sens.sens.readline
        #print('configdict:', ans)

    def join_threads(self):
        """waits until all running threads are finished"""
        try:
            self.emodulcalib.thread.join()
        except:
            print("emodulcalib thread wasn't running")
        try:
            self.weightcalib.thread.join()
        except:
            print("weightcalib thread wasn't running")
        try:
            self.thread.join()
        except:
            print("beamcalib thread wasn't running")
        

    def enablechooseframe(self):
        """enables the frame to choose beams"""
        self.emodulcalib.updatetare=False
        self.weightcalib.running=False
        # self.join_threads()
        time.sleep(0.5)
        self.updatetare = True
        self.update_distlbl() # start thread in chooseframe
        print(self.update_distlbl())
        self.calibframe.disable()
        self.chooseframe.enable()
      
    def enablecalibframe(self):
        """enables calib frame in general"""
        self.emodulcalib.updatetare = False
        self.updatetare = False
        self.weightcalib.running= False
        # self.join_threads()
        time.sleep(0.5)
        self.chooseframe.disable()
        self.calibframe.enable()

    def make_emodulcalib(self):
        """enables emodulcalib frame"""
        self.weightcalib.running=False
        self.updatetare = False
        # self.join_threads() # wait for threads to finish
        time.sleep(0.5)
        self.emodulcalib.updatetare=True 
        self.emodulcalib.update_distlbl() # start thread in emodulcalib frame
        self.weightcalib.grid_forget()
        self.emodulcalib.grid(row=1,column=0,columnspan=2)
       
    def make_weightcalib(self):
        """enables weightcalib frame"""
        self.emodulcalib.updatetare=False
        self.updatetare = False
        #self.join_threads() # wait for thread to finish
        time.sleep(0.5)
        self.weightcalib.running= True
        self.weightcalib.update_distlbl() # start thread in weightcalib
        self.emodulcalib.grid_forget()
        self.weightcalib.grid(row=1,column=0,columnspan=2)
    
    def calculate(self):
        """calculates the conversionfactor, sets the current beam, 
        passes all relevant values to forceconversion and sensor"""
        FC.forcelength = float(self.forcelengthentry.get())
        FC.measurelength = float(self.measurelengthentry.get())
        self.beam = self.choosebox.get()
        print("beam selected for conversion factor: ", self.beam)
        self.beamfact = sens.beamdict[self.beam]
        self.testfact = FC.calc_testfact()
        sens.conversionfactor = self.beamfact/self.testfact
        sens.current_beam = self.beam

class WeigthCalib (ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.updatetare = True # controls the part of the thread updating the tarelbl
        
        # varibles used to store the calibdata that will be saved
        self.calibdata={} 
        self.calibmetadata=[]
        #======================================
        # initialise the paramsframe
        #======================================

        self.paramsframe = ttk.Labelframe(self, text='parameter')
        self.paramsframe.grid(row=0,column=0)

        self.params = ['Material','distance to force application (mm)','width (mm)', 'thickness (mm)', 'distance to measuring point (mm)']
        self.labels = []
        self.entries = []
        for i in range(len(self.params)):
            self.labels.append(ttk.Label(self.paramsframe, text = self.params[i]))
            self.entries.append(ttk.Entry(self.paramsframe))
            self.labels[i].grid(row=i, column=0)
            self.entries[i].grid(row=i, column=1)
        self.tarelbl = ttk.Label(self.paramsframe,text='distance to beam')
        self.taredistlbl = ttk.Label(self.paramsframe,text='--')
        self.tarebtn = ttk.Button(self.paramsframe,text='tare',command=self.tare)
        self.undotarebtn = ttk.Button(self.paramsframe,text='undo tare',command=self.undo_tare)
        self.tarelbl.grid(row=len(self.params)+1,column=0)
        self.taredistlbl.grid(row=len(self.params)+1,column=1)
        self.tarebtn.grid(row=len(self.params)+1,column=2)
        self.undotarebtn.grid(row=len(self.params)+2,column=2)

        #=============================================
        # initialise self.collectdata
        #=============================================
       
        self.collectdata = dFrame(self, text='collect data')
        self.collectdata.grid(row=0,column=2)

  
        ## initialise lists
        self.dist = ['deflection in ' + sens.configdict['uom']]
        self.weight = ['mass in g'] 
        
        ## initialise gui features
        self.disttitle = ttk.Label(self.collectdata, text = self.dist[0])
        self.weighttitle = ttk.Label(self.collectdata, text = self.weight[0])
        self.distlbls = []
        self.weightlbls = []
        self.distlbl = ttk.Label(self.collectdata, text='--')
        self.weightentry = ttk.Entry(self.collectdata)
        self.setbtn = ttk.Button(self.collectdata, text='set', command=self.setweight)
        self.undo = ttk.Button(self.collectdata,text='undo last', command=self.undolast)
        self.clear = ttk.Button(self.collectdata,text='clear all',command=self.clearall)

        ## assemble features in mainframe
        self.disttitle.grid(row=0,column=0)
        self.weighttitle.grid(row=0, column=1)
        self.distlbl.grid(row=len(self.dist)+1, column=0)
        self.weightentry.grid(row=len(self.weight)+1,column=1)
        self.setbtn.grid(row=len(self.weight)+1,column=2)
        self.undo.grid(row=len(self.weight)+2,column=1)
        self.clear.grid(row=len(self.weight)+2,column=2)

        #===================================
        # initialise calcemodul
        #===================================
        self.calcframe = ttk.Labelframe(self, text='conversion factor')
        self.calcframe.grid(row=1,column=0,columnspan=2)

        self.calcbtn = ttk.Button(self.calcframe, text="calculate", command=self.calculate)
        self.Emodmean = ttk.Label(self.calcframe, text="mean Young's modulus (MPa): ")
        #self.range = ttk.Label(self.calcframe, text='range: ')
        # self.absDev = ttk.Label(self.calcframe, text='absolute Derivation: ')
        self.stDev = ttk.Label(self.calcframe, text='standard Derivation: ')

        self.factmean = ttk.Label(self.calcframe, text='mean conversion factor:')
        #self.factrange = ttk.Label(self.calcframe, text='range: ')
        # self.factabsDev = ttk.Label(self.calcframe, text='absolute Derivation: ')
        self.factstDev = ttk.Label(self.calcframe, text='standard Derivation: ')

        self.savebtn = ttk.Button(self.calcframe,text='save',command = self.save, state='disabled')
      


        self.calcbtn.grid(row=0, column=0)
        self.Emodmean.grid(row=1, column=0)
        self.factmean.grid(row=2, column=0)
        self.savebtn.grid(row=0,column=1,rowspan=3)
        # self.stDev.grid(row=1, column=2)
        # self.absDev.grid(row=1, column=2)  
        #start thread
        # self.update_distlbl()

        #self.collectdata.disable()
    
    def tare(self):
        """pass the tared distance to forceconversion, stop updating the tarelbl"""
        self.tared = float(self.taredistlbl.cget('text'))
        print(self.tare)
        FC.tare = self.tared
        self.updatetare=False
        #self.collectdata.enable()
    
    def undo_tare(self):
        """restarts the thread to update the tarelbl"""
        self.updatetare = True
        

    def make_calibmetadata(self):
        """ makes a list out of several metadata lists.
        This list is passed to the save_with_metadata function"""
        self.running = False
        # self.thread.join()
        time.sleep(0.5)
        self.temp = sens.get_temp()
        self.light = sens.get_lightpower()
        templist = ['temperature', self.temp]
        speed = ['samplerate', str(round((2**sens.configdict['avg']*sens.configdict['sampleClkPer'])**(-1),2))+' samples/s']
        average = ['average over x measurements', 2**sens.configdict['avg']]
        lintensity = ['lightintensity',self.light] 
        beamlist = ['beam',self.beam]
        forcedist = ['forcedistance',FC.forcelength]
        measdist = ['measuredistance',FC.measurelength]
        convfact = ['resulting conversionfact',self.beamfact]
        tare = ['taredist',FC.tare]
        self.calibmetadata = [templist,speed, average, lintensity, beamlist, forcedist,measdist,convfact,tare]
        return self.calibmetadata

    

    def save(self):
        """saves the beamname and its beamfactor (E*I) to a yaml file and updates sens.beamdict
        also saves calibdata and calibmetadata to a csv file. the location can be choosen in the browser"""
        self.material = self.entries[0].get() 
        self.thickness = self.entries[3].get()
        self.width = self.entries[2].get()
        self.beam = self.material + self.thickness + 'x' + self.width # gives a name to the beam
        self.I = FC.calc_I() 
        self.beamfact = FC.meanE*self.I # calculates the factor dependent on the beam
        sens.current_beam = self.beam 
        sens.beamdict[self.beam] = self.beamfact #adds the beam and beamfact to the beamdict 
        save.dict_as_yaml(sens.beamdict,'beams.yaml') #
        # make the calib data that will be stored in the csv file
        self.calibdata[self.dist[0]]=self.dist[1:] 
        self.calibdata[self.weight[0]]=self.weight[1:]
        self.Emod = []
        for i in FC.E:
            self.Emod.append(i)
        self.calibdata["Young's modulus"]=self.Emod
        self.calibmetadata = self.make_calibmetadata()
        save.save_with_metadata(self.calibmetadata,self.calibdata)
   
    def rearrange(self):
        """rearranges the distance and mass labels"""
        for i in range(len(self.distlbls)):
            #self.distlbls[i].grid_forget()
            self.distlbls[i].grid(row=i+1, column=0)
        for i in range(len(self.weightlbls)):
            #self.weightlbls[i].grid_forget()
            self.weightlbls[i].grid(row=i+1, column=1)
        self.distlbl.grid(row=len(self.dist)+1, column=0)
        self.weightentry.grid(row=len(self.weight)+1,column=1)
        self.setbtn.grid(row=len(self.weight)+1,column=2)
        self.undo.grid(row=len(self.weight)+2,column=0)
        self.clear.grid(row=len(self.weight)+2,column=1)

    def undolast(self):
        """deletes the last mass entry and the corresponding distance"""
        self.distlbls[-1].grid_forget()
        self.weightlbls[-1].grid_forget()
        del self.distlbls[-1]
        del self.weightlbls[-1]
        del self.dist[-1]
        del self.weight[-1]
        self.rearrange()

    def clearall(self):
        """deletes all weightcalibration made so far"""
        for i in self.distlbls:
            i.grid_forget()
        for j in self.weightlbls:
            j.grid_forget()
        del self.distlbls[:]
        del self.weightlbls[:]
        del self.dist[1:]
        del self.weight[1:]
        self.rearrange()

    def setweight(self):
        """ appends distance and weight values to the respective lists 
        and rearranges the gui"""
        self.distvalue = round(float(self.distlbl.cget("text")),4)
        self.weightvalue = round(float(self.weightentry.get()),4)
        self.dist.append(self.distvalue)
        print(self.dist)
        self.weight.append(self.weightvalue)
        self.distlbls.append(ttk.Label(self.collectdata, text=self.distvalue))
        self.weightlbls.append(ttk.Label(self.collectdata, text=self.weightvalue))

        self.rearrange()

        self.weightentry.delete(0,'end')
        self.weightentry.focus()

    def update_distlbl(self):
        """ constantly updates the distance value"""
        def run():
            print("weightcalib thread started")
            while self.running:
                sens.sens.write(b'/T \r\n')
                self.target = con.make_dict(sens.sens.readline(),sens.channel)
                print("readline: ", sens.sens.readline())
                print("channel: ", sens.channel)
                print("target: ", self.target)
                self.distance = self.target['distn'] 
                self.deflection = round((self.distance-FC.tare),4)
                #self.dstance = sens.emptystreamdict['distn2'][-1]
                if self.updatetare:
                    self.distlbl.configure(text=self.deflection)
                    self.taredistlbl.configure(text=self.distance)
                else:
                    self.distlbl.configure(text=self.deflection)
                # print(self.distance)
            print("weight calib thread stopped")
        self.thread = Thread(target = run) 
        self.thread.start()   

        #=======================================
        # functions for calcframe
        # ======================================        

    def calculate(self):
        """calculates the beamfactor and the conversionfactor,enables the savebutton"""
        FC.dist = self.dist[1:] #the first entry is omitted because it is a string
        FC.weight = self.weight[1:] # same
        FC.thickness = float(self.entries[3].get())
        FC.width = float(self.entries[2].get())
        FC.forcelength = float(self.entries[1].get())
        FC.measurelength = float(self.entries[4].get())
        FC.E = []
        FC.E = FC.calculate_Emodul()
        print(FC.E)
        FC.calc_conversion_fact()
        FC.precision()
        self.factmean.configure(text = 'mean conversion factor: '+ str(round(FC.meanfact,3)))
        self.Emodmean.configure(text="mean Young's modulus : " + str(round(FC.meanE,3)))
        # self.range.configure(text="range: "+ str(round(FC.rangeE,3))
        # self.stDev.configure(text='standard Deviation: ' + str(round(FC.stdevE,3))
        sens.conversionfactor = FC.meanfact # pass the mean conversionfactor to sensor
        self.savebtn.state(['!disabled']) # this is somehow not working



class EmodulCalib (ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.updatetare = False # controls the thread updating the tarelbl
        
        #======================================
        # initialise the paramsframe
        #======================================

        self.paramsframe = ttk.Labelframe(self, text='parameter')
        self.paramsframe.grid(row=0,column=0) 

        self.params = ['Material','distance to force application','width', 'thickness', 'distance to measuring point', "Young's modulus"]
        self.labels = []
        self.entries = []
        for i in range(len(self.params)):
            self.labels.append(ttk.Label(self.paramsframe, text = self.params[i]))
            self.entries.append(ttk.Entry(self.paramsframe))
            self.labels[i].grid(row=i, column=0)
            self.entries[i].grid(row=i, column=1)
        self.tarelbl = ttk.Label(self.paramsframe,text='distance to beam')
        self.taredistlbl = ttk.Label(self.paramsframe,text='--')
        self.tarebtn = ttk.Button(self.paramsframe,text='tare',command=self.tare)
        self.undotarebtn = ttk.Button(self.paramsframe,text='undo tare',command=self.undo_tare)
        self.tarelbl.grid(row=len(self.params)+1,column=0)
        self.taredistlbl.grid(row=len(self.params)+1,column=1)
        self.tarebtn.grid(row=len(self.params)+1,column=2)
        self.undotarebtn.grid(row=len(self.params)+2,column=2)

        self.calcframe = ttk.Labelframe(self,text='conversion factor')
        self.calcbtn = ttk.Button(self.calcframe, text='calculate', command=self.calculate)#possibility of explaining how it is calculated
        self.factorlbl = ttk.Label(self.calcframe, text='conversion factor: ')
        self.savebtn = ttk.Button(self.calcframe, text='save',command=self.save,state='disabled')

        self.calcframe.grid(row=1)
        self.calcbtn.grid(row=len(self.params),column=0)
        self.factorlbl.grid(row=len(self.params)+1,column=0)
        self.savebtn.grid(row=len(self.params),column=1,rowspan=2)
    
    def tare(self):
        """passes the tare value to forcecoonversion"""
        self.tared = float(self.taredistlbl.cget('text'))
        print(self.tared)
        FC.tare = self.tared
        self.updatetare=False    

    def undo_tare(self):
        """restarts the thread to update the tarelbl"""
        self.updatetare = True
        self.update_distlbl()

    def calculate(self):   
        """calculates the conversionfactor and passes it to the sensor"""
        FC.thickness = float(self.entries[3].get())
        FC.width = float(self.entries[2].get())
        FC.forcelength = float(self.entries[1].get())
        FC.measurelength = float(self.entries[4].get())
        #FC.tare = floeat(self.entries[].get())
        FC.E = float(self.entries[5].get())
        FC.calc_conversion_fact()
        self.factorlbl.configure(text = 'conversion factor: '+ str(round(FC.convfact,3)))
        sens.conversionfactor = FC.convfact
        self.savebtn.state(['!disabled'])

    def save(self):      
        """saves the beamname and its beamfactor (E*I) to a yaml file and updates sens.beamdict"""
        self.material = self.entries[0].get() 
        self.thickness = self.entries[3].get()
        self.width = self.entries[2].get()
        self.beam = self.material + self.thickness + 'x' + self.width
        self.I = FC.calc_I()
        self.beamfact = FC.E*self.I
        sens.current_beam = self.beam
        sens.beamdict[self.beam] = self.beamfact 
        save.dict_as_yaml(sens.beamdict,'beams.yaml')

    def update_distlbl(self):
        """ constantly updates the distance value"""
        def run():
            print("emodulcalib thread started")
            while self.updatetare:
                sens.sens.write(b'/T \r\n')
                self.target = con.make_dict(sens.sens.readline(),sens.channel)
                self.distance = self.target['distn'] 
                #self.dstance = sens.emptystreamdict['distn2'][-1]
                
                self.taredistlbl.configure(text=self.distance)
                
                # print(self.distance)
            print("emodulcalib thread stopped")
        self.thread = Thread(target = run) 
        self.thread.start()   


if __name__ == "__main__":

    root = tk.Tk()
    app = CalibWindow(root)
    app.pack()
    root.mainloop()

        
    







    
