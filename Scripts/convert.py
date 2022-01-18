# This will convert any output of the sensor to a dictionary
#or a streamdictionary
import save 
import convert as con


def string_to_list(string):
    """creates a list out of a string by making an Item out of every word"""
    
    list_ans = []
    a = 0
    string = string.decode()                       
    string = string.rstrip()                       # eliminates \n if present
    for i in range (len(string)):                  # iterates through the string
        if string[i] == ' ' and string[i+1] ==' ': # handles double spaces
            continue
        elif string [i] == ' ':
            list_ans.append(string[a:i])           # appends the words to the list
            #print(string[a:i])
            a = i+1
            #print(a)   
    list_ans.append(string[a:])                   
    name = list_ans.pop(0)                         # the first value of the list is the name of the dict
    return list_ans


def is_int(input):
    """checks whether input can be converted to int"""
    try:        
        num = int(input)
    except ValueError:
        return False
    return True

def is_float(input):
    """Checks whether input can be converted to float"""
    try:
        num = float(input)
    except ValueError:
        return False
    return True

def string_to_num(string):
    """converts a string to an int or float if possible,
       if there is a '"' it will be omitted"""
    if is_int(string):
        string = int(string)
    elif is_float(string):
        string = float(string)
    else:                           # converts all numbers to float, idk why
        if string[0] == '"':
            num = string[1:]
            #print('>',num,'<')
            if is_int(num):
                num = int(num)
                string = num
            if is_float(num):
                num = float(num)
                string = num
        elif string[len(string)-1] == '"':
            num = string[:len(string)-1]
            #print('>',num,'<')
            if is_int(num):
                num = int(num)
                string = num
            if is_float(num):
                num = float(num)
                string = num
    return string  

def item_to_num(listing): # can be applied for stream data or get target command, does not work with""
    """converts all items in lists that can be converted to either int or float"""
    for i in range(len(listing)):
        if isinstance(listing[i], list):
            for j in range(len(listing[i])):
                listing[i][j]= string_to_num(listing[i][j])
             
        elif isinstance(listing[i], str):
            listing[i] = string_to_num(listing[i]) 
    return listing      
    
   
def cut_list(listing):  
    """creates another list of words between ".." and nests it at the original place"""
    anf = []
    end = []
    for i in range(len(listing)):      # finds where ".. begins and ends .."
        if len(listing[i]) > 1:        # used to hamdle single "
            if listing [i][0] == '"' and listing[i][len(listing[i])-1] != '"':
                anf.append(i)
            elif listing[i][0] != '"' and listing[i][len(listing[i])-1] == '"': 
                end.append(i+1)
        elif listing[i] == '"':
            anf.append(i)
    #print(anf)
    #print(end)        
    for i in reversed(range(len(anf))):      # iterates through anf from the back to avoid shifting of numbres in list 
        nested_list = listing[anf[i]:end[i]] # creates a list of ".."
        del listing[anf[i]:end[i]]           # insert that list into the first list
        listing.insert(anf[i], nested_list)  
    return listing       
      
def list_to_dict(list):
    """creates a dictionary out of a list
    assuming the list is written in alternating kwarg, arg,...
    the dictionary will be written as {kwarg:arg,..}. The first entry in the list is 
    ommited, because that is usually a name"""
    dictio = {}
    for i in range(0,len(list),2):# iterates through every second item of a list list starting at the second value
        dictio[list[i]] = list[i+1]
    return dictio

def list_to_streamdict(list):
    """creates a dictionary out of a list
    assuming the list is written in kwarg, arg,...
    the dictionary will be written as {kwarg:[arg],  }"""    
    dictio = {}
    for i in range(1,len(list),2):
        list[i] = [list[i]]
        print(list[i])
    # print("List[1]", list[1])
    for i in range(0,len(list),2):
        dictio[list[i]] = list[i+1]
    return dictio

def apply_channel(dict,channel):
    """modifies the streamdict according to the channel selected
    
    if channel is 1 all kwargs containing 2 will be deleted,
    if channel is 2 all kwargs not containig 2, except temp and cs,will be deleted
    '2' will be removed from all other kwargs"""
    delete =[]
    rename = []

    for i in dict:
        if channel == 1:
            if '2' in i:
                delete.append(i)              
        elif channel == 2:
            if '2' not in i and i != 'temp' and i!='cs':
                delete.append(i)
            elif i != 'temp' and i!='cs':
                rename.append(i)
    for i in delete:
        del dict[i]
    for i in rename:
        newname = i[:len(i)-1]
        dict[newname] = dict.pop(i)
    #print("dict apply channel", dict)
    return dict

def make_streamdict(input, channel, omitted = 1):
    """converts a list of or a byteencoded string input to a streamdict

    The string has to be a name and then alternating kwarg, arg;
    the items of the list have to be such strings
    the first and last entry of the list will be ommitted
    number values are converted to int or float. Depending on the channel 
    values for a specific sensor or both sensors will be used"""
    if type (input) == bytes:
        print("input", input)
        dict = list_to_streamdict(item_to_num(string_to_list(input)))
    else: # if the input is a list (from readlines) the first entry, which is the header will be ommitted
        dict = list_to_streamdict(item_to_num(string_to_list(input[omitted])))
        for i in range(omitted+1,len(input)-1): #the first and last entry are ommitted
            dicti = list_to_dict(item_to_num(string_to_list(input[i])))
            for i in range(len(dict)):
                [*dict.values()][i].append([*dicti.values()][i])
    apply_channel(dict, channel=channel)
    save.streamdict_to_csv(dict,'stream.csv')
    return dict    

def append_to_streamdict(dict,input,channel, omitted = 1):
    """ appends a list of or a byteencoded string to a streamdict, 
    the args will be appended to the respective list of args.
    Returns a list containing the updated streamdict, the value of streamerror
    and the streamdict formed by reading the buffer"""
    #print(input)
    try:
        if type(input) == bytes:
            if b'stop' in input: #checks if the inpot is a stop flag
                #print(input)
                dictio = None
                streamerror = True
            elif b"stream" in input: #checks if the input is a header
                #print(input)
                dictio = None
                streamerror = True
            else:
                dictio = make_dict(input,channel=channel)
                #print(True)
                for i in range(len(dict)):
                    [*dict.values()][i].append([*dictio.values()][i])
                    #print([*dict.values()][i])
                #length = 1
                save.append_to_csv(dict,'stream.csv')
                streamerror = False
        else:
            dictio = make_streamdict(input,channel=channel, omitted=omitted)            
            #print("streamdict to append: ", dictio)
           # print('made dictio')
            length = len([*dictio.values()][0])
            for i in range(len(dict)):  #iterates through the values  
                for a in range(len([*dictio.values()][i])):   #iterates through the valuelist 
                   [*dict.values()][i].append([*dictio.values()][i][a])
            #print("final streamdict: ",dict)
            #print('madefinal streamdict')
            #save.streamdict_to_csv(dict,'stream.csv')
            streamerror = False # indicates whether there was an error or not
    except: # This catches a very weird error that sometimes happens when the sensor is confused
            # it is not a problem of the sensor, I checked that with the company, there must be some
            # very weid bug in the programme that I haven't found yet.
            # after this exception, saving the measured data might not work
        #print('There is no signal from the sensor')
        #print('Loop except')
        lengthlist=[]
        for i in range(len(dict)):
            lengthlist.append(len([*dict.values()][i]))
        #try:
        #    print(dictio)
        #except:
        #    print('no dictio cause listindex out of range')
        #print(dict)
        #print('length of the lists in the emptystreamdict', lengthlist)
        streamerror = True
    try:
        return dict, streamerror, dictio
    except:
        return dict, streamerror

def make_dict(string,channel):
    """converts a string to a dictionary, numbers will be converted to floats

    String has to be name and then alternating kwarg,arg
    values in "" are treated as one otherwise spaces are seperators"""
    dict1 = list_to_dict(item_to_num(cut_list(string_to_list(string))))
    print("dict", dict1)
    #print("make_dict: ", dict)
    apply_channel(dict1,channel=channel)
    return dict1  

def make_stringdict(string,channel):
    """converts a string to a dictionary, numbers will remain strings

    String has to be name and then alternating kwarg,arg
    values in "" are treated as one otherwise spaces are seperators"""
    dict = list_to_dict(cut_list(string_to_list(string)))
    apply_channel(dict,channel=channel)
    return dict 

def append_dict_to_streamdict(streamdict,dictio,channel):
    apply_channel(dict=dictio,channel=channel)
    length = len([*dictio.values()][0])
    for i in range(len(streamdict)):  #iterates through the values  
        for a in range(len([*dictio.values()][i])):   #iterates through the valuelist 
            [*streamdict.values()][i].append([*dictio.values()][i][a])
    #print("final streamdict: ",streamdict)


    
#variables for debugging        
l = [b'T stream ascii TpckCnt 1 cs 971\n', 
b'T  temp 28.1 signal 1.054920 snr 2 distn 974.6508 distf 0.000000 refp 1.5 signal2 0.519810 snr2 6 distn2 859.7958 distf2 0.000000 refp2 1.5 cs 264c\n', 
b'T  temp 28.1 signal 1.054605 snr 2 distn 974.5059 distf 0.000000 refp 1.5 signal2 0.519807 snr2 6 distn2 859.6247 distf2 0.000000 refp2 1.5 cs 2648\n', 
b'T  temp 28.1 signal 1.054723 snr 2 distn 974.5604 distf 0.000000 refp 1.5 signal2 0.520032 snr2 6 distn2 859.6890 distf2 0.000000 refp2 1.5 cs 2637\n', 
b'stop cs 2e6\n']
# d = {'temp': [32.0, 32.0, 32.1, 32.1, 32.1], 'signal': [1.053653, 1.053861, 1.053704, 1.053641, 1.053644], 'snr': [2, 2, 2, 2, 2], 'distn': [974.0677, 974.1634, 974.091, 974.062, 974.0633], 'distf': [0.0, 0.0, 0.0, 0.0, 0.0], 'refp': [1.5, 1.5, 1.5, 1.5, 1.5], 'signal2': [0.478151, 0.478103, 0.478284, 0.478206, 0.478118], 'snr2': [7, 7, 7, 7, 7], 'distn2': [859.1071, 859.2202, 859.1346, 859.1004, 859.1019], 'distf2': [0.0, 0.0, 0.0, 0.0, 0.0], 'refp2': [1.5, 1.5, 1.5, 1.5, 1.5], 'cs': [2618, '260d\n', 2618, 2607, 2616]}
# s = b'T  temp 28.1 signal 1.054920 snr 2 distn 974.6508 distf 0.000000 refp 1.5 signal2 0.519810 snr2 6 distn2 859.7958 distf2 0.000000 refp2 1.5 cs 264c\n'

#dict = make_streamdict(l)
#print(dict)
#dict2 = append_to_streamdict(dict,s)
#print(dict2)
#dict3 = make_dict(s)
#print(dict3)
# l = ['avg', '12', 'avgDef', '255', 'calTable', '1', 'uom', 'um', 'setTemp', '32', 'gain', '100', 'Dpeak', '1.000000', 'TformatDef', '127', 'Tformat', '127', 'fwVer', '2.8050', 'serial', '2421', 'sign', '""', 'bps', '19200', 'snrMax', '230', 'calTableMax', '12', 'analog1', '1', 'analog2', '3', 'cmdLenMax', '90', 'bpsRange', '"9600', '19200', '28800', '38400', '57600', '62500', '76800', '115200', '125000', '200000', '250000"', 'sampleClkPer', '9.600000E-05', 'RCDcode', 'R', 'HWcode', 'muDMS', 'chCnt', '2', 'TchSelect', '3', 'calTable2', '1', 'gain2', '100', 'Dpeak2', '1.000000', 'sign2', '""', 'cs', '7201']
# d = list_to_dict(item_to_num(cut_list(l)))
# print(d)
##
##
##print(l1)

# d = make_streamdict(l,2)
# print(d)
# d2 = append_to_streamdict(d,s,2)

# print(d2)
