import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from sensor import sens
import convert as con
import save
from threading import Thread
import time
from forceconversion import FC
import timeit
import statistics as st
#from binarystream import b
from filelock import Timeout, FileLock

lock = FileLock("high_ground.txt.lock")

class Measure(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.timestamp = []
        self.running = False
        # variables for the graph
        self.fig = Figure(figsize=(6,5), dpi=100)
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_xlabel('time, s')
        self.ax1.set_ylabel('force, mN')
        self.ax1.set_title('Force Measurement')
        self.streamdict = sens.emptystreamdict
        self.running = False
        self.plotforce = True

        # building gui        
        self.build_graphframe(self)
        self.build_controlframe(self)  
        self.build_saveframe(self)

        self.graphframe.grid(row=0,column=1,rowspan=2,sticky='nsew')  
        self.controllframe.grid(row=0,column=0)
        self.saveframe.grid(row=1,column=0)
        sens.make_configdict()
        print("Configdict",sens.configdict)
        
        self.sampleperiod = 2**sens.configdict['avg']*sens.configdict['sampleClkPer']
        #self.anim = animation.FuncAnimation(self.fig, self.animate)
        #self.anim.event_source.stop()

        # create lock for buffer.txt
        self.lock = FileLock("buffer.txt.lock")
    
    def build_graphframe(self,parent):


        self.graphframe = tk.Frame(parent)        
    
        self.canvas = FigureCanvasTkAgg(self.fig, self.graphframe)

        #self.canvas.draw()

        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.graphframe)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)


    def build_controlframe(self,parent):

        self.v = tk.IntVar()
        self.controllframe = ttk.Labelframe(parent,text='control graph')              
        
        self.label = tk.Label(self.controllframe, text='Streames data')
        self.label.grid(row=0,column=0,columnspan=3)
        
        onbutton = tk.Button(self.controllframe, text='start', command=self.switchon)
        onbutton.grid(row=1,column=0)

        offbutton = tk.Button(self.controllframe, text='stop', command=self.switchoff)
        offbutton.grid(row=1,column=1)

        clearbutton = tk.Button(self.controllframe,text='clear',command=self.clear)
        clearbutton.grid(row=1, column=2)

        self.distplt = tk.Radiobutton(self.controllframe,text='plot distance',variable=self.v,value=1,command=self.pltdist)
        self.distplt.grid(row=2,column=0)

        self.forceplt = tk.Radiobutton(self.controllframe,text='plot force',variable=self.v,value=2,command=self.pltforce)
        self.forceplt.grid(row=2,column=1)

    def build_saveframe(self,parent):
        self.saveframe = ttk.Labelframe(parent, text='save')
        self.savebtn = tk.Button(self.saveframe,text='save as',command=self.save)
        self.savebtn.grid(row=1,column=1)

    def save(self):
        """ saves data and metadata to a folder that can be selected via the gui"""
        print("HELLO")
        metadata = sens.make_metadata()
        metadata.append(["start time: ",self.starttime])
        print("starttime: ", self.starttime)
        data = sens.make_data()   
        print("saving metdata: ", metadata)
        print("saving data: ", data)
        save.save_with_metadata(metadata,data)

    def save_temp(self):
        """ saves data and metadata to current folder with name "test_temp.csv" """
        metadata = sens.make_metadata()
        metadata.append(["start time: ",self.starttime])
        print("starttime: ", self.starttime)
        data = sens.make_data()   
        print("saving metdata: ", metadata)
        print("saving data: ", data)
        save.save_with_metadata_temp(metadata,data)
    
    def pltdist(self):
        """plots distance over time in the graph"""
        self.plotforce=False

    def pltforce(self):
        """plots force over time in the graph"""
        self.plotforce = True

    def switchon(self): 
        """starts the data stream the plotted data depends on whether self.plotforce= true or false
        creates a new graphframe on top of the old one"""
        print('switch on')
        self.running = True # used by clearbtn and make_buffer
        self.starttime = time.time()
        print("starttime: ",self.starttime)
        sens.sens.write(b'/T stream ascii\r\n')
        # sens.sens.write(b'/T \r\n')
        #time.sleep(0.1)
        # self.header = sens.sens.readline()
        # print('header',self.header)
        self.make_buffer1()
        #self.append_to_dicts()
        #self.timeafterheader = time.time()

        try:
            self.build_graphframe(self)
        #  print("graphframe built")
            self.graphframe.grid(row=0,column=1,rowspan=2,sticky='nsew')#maybe find a better solution
        # print("graphframe placed")
            self.anim = animation.FuncAnimation(self.fig, self.animate) 
        # print("animation made")
            self.anim.event_source.start()
        except:
            print("no animation")
            
       # print("animation start")
        self.endswitchon=time.time()
        print("switchontime",self.endswitchon-self.starttime)
        #print("start to header: ", self.timeafterheader-self.starttime)
        #print("header to end", self.endswitchon-self.timeafterheader)
        
              
        
    def switchoff(self): 
        """stops the datastream and the animation,
        reads out the buffer and appends its content to sens.emptystreamdict.
        Checks how many entrys where in the buffer and appends that many entrys to the timelist.
        Saves the streamdict to a file specified in save.py, in case someone wants to look at 'raw' data"""
        sens.sens.write(b'/stop\r\n')
        time.sleep(0.1)
        self.running = False
        self.bufferthread.join()
        ## self.appendingthread.join()
        self.endtime = time.time()
        print('switch off')     
        self.anim.event_source.stop()       
        #time.sleep(1)
        try:
            ans = save.string_from_txt('buffer.txt',True)
        except:
            print('No ans')
        for i in range(len(ans)):
            ans[i] = ans[i].encode()
        #print(ans)
        try:        
            self.buffer = con.append_to_streamdict(sens.emptystreamdict,ans,sens.channel,omitted = 0)
            sens.make_forcelist()
            #print(self.buffer)
           # print('madebuffer')
            #print('list: ', self.buffer[2]['temp'])
            for i in range(len(self.buffer[2]['temp'])):
                #print('i: ',i)
                # iterates through the time list of the buffer-streamdict 
                # for every entry a timestamp is appended to timelist
                sens.timelist.append(sens.timelist[len(sens.timelist)-1]+ self.sampleperiod)
        except:
            print('There was some problem with reading out the buffer')
        save.streamdict_to_csv(sens.emptystreamdict) 
        # this saves the streamdict to a file specified in save.py
        #self.timedifferences()
        
        # should update the plot, doesn't really work but is not very important
        try:
            self.ax1.clear()  
            if self.plotforce:
                self.ax1.plot(sens.timelist,sens.forcelist)
                self.ax1.set_ylabel('force, mN')
                self.ax1.set_title('Force Measurement')
            else:   
                self.ax1.plot(sens.timelist, self.deflectionlist) 
                self.ax1.set_title('Distance Measurement')
                self.ax1.set_ylabel('dist, ', sens.configdict['uom'])
            self.ax1.set_xlabel('time, s')
        except:
            print('unable to clear axis')
        self.fig.tight_layout()
       # self.fig.draw(self.canvas)
        print('whats wrong?')
        
        return dict        

    def start_stop_func(self):
        """prints the time needed by run() over 100000 executions"""
        def run():
            sens.sens.write(b'/T stream ascii\r\n')
            sens.sens.write(b'/stop\r\n')
        overalltime = timeit.timeit(run, number=100000)
        singletime = overalltime/100000
        print("overall time: ", overalltime)
        print("single time: ", singletime)
        

    def timedifferences(self):
        """prints the timedifference between the two timestamps and the time measured by the sensor"""
        self.realtimediff= self.endtime-self.starttime
        self.sensortimediff = sens.timelist[-1]-sens.timelist[0]
        #print the time passed according to start and endtime
        print("time passed according to start and endtime", self.realtimediff)
        #print the time passed according to timelist
        print("time passed according to sensor", self.sensortimediff)
        print("realtime - sensortime: ", self.realtimediff-self.sensortimediff)
        #print("time for printing header: ", self.timeafterheader-self.starttime)
        print("maximum time for one animation: ", max(self.timestamp))
        print("minimum time for one animation: ", min(self.timestamp))
        print("mean time for one animation: ", st.mean(self.timestamp))
        print("stdev time for one animation: ", st.stdev(self.timestamp))

    def clear(self):
        """ stops streaming, clears the streamdict, forcelist and timelist, starts streaming again
        if streaming was stopped before (self.running=False), it just clears everything without restarting"""
        if self.running:
            self.switchoff()
            sens.emptystreamdict = sens.make_emptystreamdict()
            print("new emptystreamdict: ", sens.emptystreamdict)
            sens.forcelist = sens.make_forcelist()
            sens.timelist=[]
            sens.timereal=[]
            self.switchon()
        else:
            #self.switchoff()
            sens.emptystreamdict = sens.make_emptystreamdict()
            print("new emptystreamdict: ", sens.emptystreamdict)
            sens.forcelist = sens.make_forcelist()
            sens.timelist=[]
            sens.timereal=[]

    def append_to_dicts(self):
        """appends the answeres from the sensor to the streamdict,
        makes a forcelist and appends time to sens.timelist.
        The function basically creates data for the animate function"""
        time_init = time.time()
        def run():            
            while self.running:
                #print('run function')
                with self.lock:
                #time.sleep(0.2)
                    ans = save.string_from_txt('buffer.txt').encode()
                  #self.startstreamdict = time.time()
                d = con.append_to_streamdict(sens.emptystreamdict, ans,sens.channel)
                #self.stopstreamdict=time.time()
                self.streamerror = d[1]
                #print('dict', len(d[0]['distn']))
                f = sens.make_forcelist()
                #print('force',len(f))
                if self.streamerror == False:
                    if len(sens.timelist) == 0:
                        #sens.timelist.append(self.sampleperiod) # the first value will be self.ampleper
                        sens.timelist.append(0)
                        sens.timereal.append(0)
                    else:
                        sens.timelist.append(sens.timelist[len(sens.timelist)-1]+ self.sampleperiod)
                        #print('sens list', sens.timelist)                        
                        sens.timereal.append(time.time()-time_init)
                        #print('Real time', sens.timereal)
                #else:
                    #print('streamerror')
                #print('time',len(sens.timelist))

                self.deflectionlist=[]
                for i in sens.emptystreamdict['distn']:
                    self.deflectionlist.append(i-FC.tare)

        self.appendingthread = Thread(target=run)
        self.appendingthread.start()

    def make_buffer(self): 
        """writes the rawanswers to a txt file"""
        def run():
            save.myfiles={}           
            ans = sens.sens.readline().decode()            
            with self.lock:
                save.string_to_txt(ans,'buffer.txt','w')
            while self.running:
                beforereading = time.time()
                ans = sens.sens.readline().decode()
                afterreading = time.time()
                print('time for reading: ', afterreading-beforereading)
                print(ans)
                with self.lock:
                    save.string_to_txt(ans,'buffer.txt','a')
        self.bufferthread = Thread(target=run)
        self.bufferthread.start()


    def make_buffer1(self):
        """uses ascii streaming, """
        self.time_init = time.time()
        def run():
            print("bufferthread started")
            while self.running == True:                
                beforereading = time.time()
                ans = sens.sens.readline()
                #print(ans)
                afterreading = time.time()
                #print("time for reading", afterreading-beforereading) 
                d = con.append_to_streamdict(sens.emptystreamdict, ans,sens.channel)
                self.streamerror = d[1]
                f = sens.make_forcelist() 
                if self.streamerror == False:            
                        #print(d)
                    if len(sens.timelist) == 0:
                        #sens.timelist.append(self.sampleperiod)
                        sens.timelist.append(0)
                        sens.timereal.append(time.time()-self.time_init)
                        #print(sens.timelist)
                        #print(sens.forcelist)
                    else:
                        sens.timelist.append(sens.timelist[len(sens.timelist)-1]+ self.sampleperiod)
                        #print('sens list', sens.timelist)                        
                        sens.timereal.append(time.time()-self.time_init)
                        #print('Real time', sens.timereal)               
                afterprocessing = time.time()
                ##print('time for reading: ', afterreading-beforereading)
                ##print('time for processing: ',afterprocessing -afterreading)
                self.deflectionlist=[]
                for i in sens.emptystreamdict['distn']:
                    self.deflectionlist.append(i-FC.tare)
            print("bufferthread stopped")
            ans = sens.sens.readlines()
            print(ans)
            print(len(ans))
        self.bufferthread = Thread(target=run)
        self.bufferthread.start()
    
    def make_buffer2(self):
        """uses byteencoded reading, works with some errors"""
        b.bytes = sens.sens.readline()
        b.set_tpackCnt()
        def run():
            print("bufferthread started")
            while self.running == True:
                beforereading = time.time()
                rbytes = sens.sens.readline()
                afterreading = time.time()
                b.bytes = bytearray(rbytes)
                b.byte_to_streamdict()
                afterprocessing = time.time()
                print('time for reading: ', afterreading-beforereading)
                print('time for processing: ',afterprocessing -afterreading)
            print("bufferthread stopped")
        self.bufferthread = Thread(target=run)
        self.bufferthread.start()

    
    def animate(self, frame):
        """function for the animation, reads data from the buffer.txt file, plots force or dist over time, 
        depending on whether self.forceplot is True or false""" 
        self.startanimtime = time.time()
        #print(self.startanimtime)
        # ans = save.string_from_txt('buffer.txt').encode()
        # print('ans',ans)
        # self.startstreamdict = time.time()
        # d = con.append_to_streamdict(sens.emptystreamdict, ans,sens.channel)
        # self.stopstreamdict=time.time()
        # print("streamdicttime", self.stopstreamdict-self.startstreamdict)
        # self.streamerror = d[1]
        # print('dict', len(d[0]['distn']))
        # f = sens.make_forcelist()
        # print('force',len(f))
        # self.deflectionlist = []
        # for i in sens.emptystreamdict['distn']:
        #     self.deflectionlist.append(i-FC.tare)
        # self.sampleperiod = 2**sens.configdict['avg']*sens.configdict['sampleClkPer']
        # if self.streamerror == False:
        #     if len(sens.timelist) == 0:
        #         #sens.timelist.append(self.sampleperiod) # the first value will be self.ampleper
        #         sens.timelist.append(0)
        #     else:
        #         sens.timelist.append(sens.timelist[len(sens.timelist)-1]+ self.sampleperiod)
        # else:
        #     print('streamerror')
        # print('time',len(sens.timelist))
        try:
            self.ax1.clear()  
            if self.plotforce:
                self.ax1.plot(sens.timelist,sens.forcelist)            
                self.ax1.set_ylabel('force, mN')
                self.ax1.set_title('Force Measurement')
            else:   
                self.ax1.plot(sens.timelist, self.deflectionlist) 
                self.ax1.set_title('Distance Measurement')
                self.ax1.set_ylabel('dist, ', sens.configdict['uom'])
            self.ax1.set_xlabel('time, s')
            self.fig.tight_layout()
            self.stopanimtime = time.time()
            self.timestamp.append(self.stopanimtime-self.startanimtime)
        except:
            self.ax1.set_xlabel('time, s')

    
    def animate2(self, frame):
        """ function for the animation, plots force or dist over time, 
        depending on whether self.forceplot is True or false. Used with the byteencoded reading""" 
        self.startanimtime=time.time()
        f = sens.make_forcelist()
        self.deflectionlist = []
        for i in sens.emptystreamdict['distn']:
            self.deflectionlist.append(i-FC.tare)
        #self.sampleperiod = 2**sens.configdict['avg']*sens.configdict['sampleClkPer']

        self.ax1.clear()  
        if self.plotforce:
            self.ax1.plot(sens.timelist,sens.forcelist)
            self.ax1.set_ylabel('force, mN')
            self.ax1.set_title('Force Measurement')
        else:   
            self.ax1.plot(sens.timelist, self.deflectionlist) 
            self.ax1.set_title('Distance Measurement')
            self.ax1.set_ylabel('dist, ', sens.configdict['uom'])
        self.ax1.set_xlabel('time, s')
        self.fig.tight_layout()
        self.stopanimtime = time.time()
        self.timestamp.append(self.stopanimtime-self.startanimtime)
        #time.sleep(0.5)

    def animate1(self, frame):
        """ function for the animation, reads out the sensor, plots force or dist over time, 
        depending on whether self.forceplot is True or false""" 
        self.startanimtime = time.time()
        ans = sens.sens.readline()
       # self.stopreadingtime=time.time()
       # print("timefor reading: ",self.stopreadingtime-self.startanimtime)
        #if ans == b"":
        #    sens.forcelist=[]
        #    self.deflectionlist=[]
        #else:
        self.startstreamdict = time.time()
        d = con.append_to_streamdict(sens.emptystreamdict, ans,sens.channel)
        self.stopstreamdict=time.time()
        print("streamdicttime", self.stopstreamdict-self.startstreamdict)
        self.streamerror = d[1]
        print('dict', len(d[0]['distn']))
        f = sens.make_forcelist()
        print('force',len(f))
        self.deflectionlist = []
        for i in sens.emptystreamdict['distn']:
            self.deflectionlist.append(i-FC.tare)
        self.sampleperiod = 2**sens.configdict['avg']*sens.configdict['sampleClkPer']
        if self.streamerror == False:
            if len(sens.timelist) == 0:
                #sens.timelist.append(self.sampleperiod)
                sens.timelist.append(0)
            else:
                sens.timelist.append(sens.timelist[len(sens.timelist)-1]+ self.sampleperiod)
        else:
            print('streamerror')
        print('time',len(sens.timelist))
        self.ax1.clear()  
        if self.plotforce:
            self.ax1.plot(sens.timelist,sens.forcelist)
            self.ax1.set_ylabel('force, mN')
            self.ax1.set_title('Force Measurement')
        else:   
            self.ax1.plot(sens.timelist, self.deflectionlist) 
            self.ax1.set_title('Distance Measurement')
            self.ax1.set_ylabel('dist, ', sens.configdict['uom'])
        self.ax1.set_xlabel('time, s')
        self.fig.tight_layout()
        self.stopanimtime = time.time()
        self.timestamp.append(self.stopanimtime-self.startanimtime)
        #time.sleep(0.5)

    def plotting(self):
        """try to plot via a thread, did not work"""
        def run():
            while self.running:
                con.append_to_streamdict(sens.emptystreamdict, sens.sens.readline(),sens.channel)
                print(sens.emptystreamdict)
                self.sampleperiod = 2**sens.configdict['avg']*sens.configdict['sampleClkPer']
                if len(sens.timelist) == 0:
                    sens.timelist.append(self.sampleperiod)
                else:
                    sens.timelist.append(sens.timelist[len(sens.timelist)-1]+ self.sampleperiod)
                print(sens.timelist)
                #print()
                self.ax1.clear()       
                self.ax1.plot(sens.timelist, sens.emptystreamdict['distn'])
                self.fig.show()
                print(2)
        thread = Thread(target=run)
        thread.start()
    
    def check_sampleCLkPer(self):
        """checks if the time needed for a measurement stays constant
        (it does stay constant)"""
        self.sampleClkPer = []
        i=0
        while i <= 500:
            sens.make_configdict()
            self.sampleClkPer.append(sens.configdict['sampleClkPer'])
            i = i+1
            print(i)
        print('maximun: ',max(self.sampleClkPer))
        print('minimum: ', min(self.sampleClkPer))
        print('mean: ', st.mean(self.sampleClkPer))
        print('stdev: ', st.stdev(self.sampleClkPer))
        

if __name__ == "__main__":
    
    root = tk.Tk()
    f = Measure(root)
    f.pack()
    root.mainloop()
