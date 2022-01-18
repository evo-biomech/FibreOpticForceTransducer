import csv
import os.path
from statistics import mean
import yaml
import tkinter.filedialog
import os



# filepath designs the dictionary where the file is saved
filepath = os.getcwd() # Curent directory
#filepath1 = "/home/localuser1/Documents/Aurelie/3D_Motor_Stages/Python/github/fibreoptics"
#filepath2 = "C:/Users/Franka/Documents/london/Fiberoptics/python/Fibreopticsensor/output"

# checks on which computer the programme is running, can be changed when running on the workstation
"""
if os.path.isdir(filepath1):
    filepath = filepath1
elif os.path.isdir(filepath2):
    filepath = filepath2
    """

myfiles ={}

class myfile():
    """keeps track of the position in the file,
    so that the same position is used after reopening"""
    myfiles = {}
    def __init__(self, fname, *args):
        super().__init__()
        #file.__init__(self, fname, *args)
        self.file = open(fname,'r')
        self.name = fname
        if self.name in myfile.myfiles:
            pos = myfile.myfiles[fname]
        else:
            pos = 0
        self.file.seek(pos)
    
    def close(self):
        myfile.myfiles[self.name] = self.file.tell()
        self.file.close(self)

def string_to_txt(string,filename,mode):
    completeFilename = os.path.join(filepath,filename)
    with open(completeFilename,mode) as file:
        file.write(string)

def delete_buffer(filename):
    completeFilename = os.path.join(filepath,filename)
    os.remove(completeFilename)

def string_from_txt(filename,readlines=False):
    """returns the current line of a .txt file"""
    #print(myfiles)
    completeFilename = os.path.join(filepath,filename)
    f = open(completeFilename,'r')
    if filename in myfiles:
        pos = myfiles[filename]
    else:
        pos = 0
    f.seek(pos)
    if readlines:
        ans = f.readlines()
    else:
        ans = f.readline()
    myfiles[filename] = f.tell()
    #print(myfiles)
    f.close()
    return ans

def streamdict_to_csv(dict, filename = 'stream.csv', mode = 'w'):
    """ prints a {kwarg,[arg],..} formatted dictionary to a csv file
    the kwargs will be the column titels, the args the columns"""
    completeFilename = os.path.join(filepath,filename)
    fieldnames = [*dict]
    rowData = zip(*[*dict.values()])
    with open (completeFilename, mode, newline = '') as csvFile:
        writer = csv.writer(csvFile,'excel')
        writer.writerow(fieldnames)
        writer.writerows(rowData)

def append_to_csv(dict, filename):
    """appends newest(last) values from a {kwarg:[arg],...} streamdict to an existing csv file"""
    completeFilename = os.path.join(filepath,filename)
    last = len([*dict.values()][0])-1
    rowData = list(zip(*[*dict.values()]))
    with open(completeFilename, 'a', newline = '') as csvFile:
        writer = csv.writer(csvFile,'excel')
        writer.writerow(rowData[last])

def dict_to_csv(dict, filename):
    """saves a dictionary in a csv file, kw in first column, args in second"""
    completeFilename = os.path.join(filepath,filename)
    valuelist = [[*dict],[*dict.values()]]
    csvlist = list(zip(*valuelist))
    with open (completeFilename,'w', newline='') as csvfile:
        writer = csv.writer(csvfile,'excel')
        writer.writerows(csvlist)

def lists_to_csv(csvlist, filename):
    """saves a list of lists in a csv file every list gets a new column"""
    completeFilename = os.path.join(filepath,filename)
    csvlist = list(zip(*csvlist))
    with open (completeFilename,'w', newline='') as csvfile:
        writer = csv.writer(csvfile,'excel')
        writer.writerows(csvlist)

def read_yamldict(filename):
    """reads data from a yaml file"""
    completeFilename = os.path.join(filepath,filename)
    with open(completeFilename) as f:
        try:
            data = yaml.load(f, Loader=yaml.FullLoader)
        except:
            data = yaml.load(f)
    return data

def dict_as_yaml(dict, filename):
    """saves a dict to a yaml file"""
    completeFilename = os.path.join(filepath,filename)
    # with open(completeFilename) as f:
    #     data = yaml.load(f, Loader=yaml.FullLoader)
    # data.update(dict) #not necessary anymore
    with open(completeFilename,'w') as f:
        yaml.dump(dict,f)
    print('saved to: '+ completeFilename)
    
def transpone(l):
    """transpones a list of multiple lists
    if the entrys do not have the same length, an empty string will be put in their place"""
    nestedlist=[]
    length=[]
    transponedlist=[]

    for i in range(len(l)):
        length.append(len(l[i]))

    for i in range(max(length)):
        for j in range(len(l)):
            try:
                nestedlist.append(l[j][i])
            except:
                nestedlist.append("")
        transponedlist.append(nestedlist)
        nestedlist=[]
    return(transponedlist)
    
def save_with_metadata(metadata, data, dir=None):
    """saves the data and the metadata to a csv file,
     the path can be choosen in the gui""" 
    root = tkinter.Tk()
    root.withdraw() #use to hide tkinter window
    if dir == None:
        currdir = os.getcwd()
    else:
        currdir = dir
    filename = tkinter.filedialog.asksaveasfilename(defaultextension='.csv',parent=root, initialdir=currdir, title='Save as')
    emptyrow = []
    fieldnames = [*data]
    rowData = transpone(list(data.values()))
    with open (filename,'w', newline='') as csvfile:
        writer = csv.writer(csvfile,'excel')
        writer.writerows(metadata)
        #streamdict_to_csv(data,filename,'a')
        writer.writerow(emptyrow)
        writer.writerow(fieldnames)
        writer.writerows(rowData)

def save_with_metadata_temp(metadata, data, dir=None):
    """saves the data and metadata to a csv file at the 
    end of the test, named "Test_temp.csv" """
    if dir == None:
        filename = "test_temp.csv"
    else:
        filename = os.path.join(dir,"test_temp.csv")
    emptyrow = []
    fieldnames = [*data]
    rowData = transpone(list(data.values()))
    with open (filename,'w', newline='') as csvfile:
        writer = csv.writer(csvfile,'excel')
        writer.writerows(metadata)
        #streamdict_to_csv(data,filename,'a')
        writer.writerow(emptyrow)
        writer.writerow(fieldnames)
        writer.writerows(rowData) 
    
    

d = read_yamldict('beams.yaml')
print(d)

    

    


    
       


    
#variable for debugging        
#d = {'temp': [32.0, 32.0, 32.1, 32.1, 32.1], 'signal': [1.053653, 1.053861, 1.053704, 1.053641, 1.053644], 'snr': [2, 2, 2, 2, 2], 'distn': [974.0677, 974.1634, 974.091, 974.062, 974.0633], 'distf': [0.0, 0.0, 0.0, 0.0, 0.0], 'refp': [1.5, 1.5, 1.5, 1.5, 1.5], 'signal2': [0.478151, 0.478103, 0.478284, 0.478206, 0.478118], 'snr2': [7, 7, 7, 7, 7], 'distn2': [859.1071, 859.2202, 859.1346, 859.1004, 859.1019], 'distf2': [0.0, 0.0, 0.0, 0.0, 0.0], 'refp2': [1.5, 1.5, 1.5, 1.5, 1.5], 'cs': [2618, '260d\n', 2618, 2607, 2616]}






    




    
    

    
   



    
    
    
    
    
