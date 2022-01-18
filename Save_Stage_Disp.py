import collections
import time
import pandas as pd
import numpy as np
import yaml
from yaml import load, dump
try:
	from yaml import CLoader as Loader, CDumper as Dumper
except:
	from yaml import Loader, Dumper



def Method_to_List(filename, Init_Pos, Final_Pos, Initial_Time, Final_Time):
	with open(filename) as file:
		try:
			List = yaml.load(file, Loader = yaml.FullLoader)
		except:
			List = yaml.load(file)
		Test_Header = ['Test settings']
		Init_Position = ['Initial position (mm)', 'X', Init_Pos[0], 'Y', Init_Pos[1], 'Z', Init_Pos[2]]	
		Init_Time = ['Initial time stage (s)',Initial_Time]
		Segment = []
		for item, doc in List.items():
			Type = doc.get('Type')
			if (Type == "Move stage"):
					Stg = doc.get('Stage')
					Dis = doc.get('Displacement')
					Vel = doc.get('Velocity')
					Segment.append(['Segment '+str(item), 'Move', Stg, Dis, 'mm', Vel, 'mm/s'])
			if (Type == "Hold"):
					t_hold = doc.get('Duration')
					Segment.append(['Segment '+str(item), 'Hold', t_hold, 's'])
			if (Type == "Preload"):
					Stg = doc.get('Stage')
					For = doc.get('Force')
					Vel = doc.get('Velocity')
					t_hold = doc.get('Duration')
					Segment.append(['Segment '+str(item), 'Preload', Stg, For, 'mN', Vel, 'mm/s', t_hold, 's'])
		Final_Position = ['Final position (mm)', 'X', Final_Pos[0], 'Y', Final_Pos[1], 'Z', Final_Pos[2]]
		Fin_Time = ['Final time stage', Final_Time]
		Metadata_Test = [Test_Header, Init_Position, Init_Time]
		for i in Segment:
			Metadata_Test.append(i)
		Metadata_Test.append(Final_Position)
		Metadata_Test.append(Fin_Time)
	return Metadata_Test

def StageDisp_To_Dict(time,Disp):
	#Time = (1:len(Disp))*freq
	Dict_Stage = {'Time in s':time,'Stage disp in mm':Disp}
	return Dict_Stage

if __name__ == "__main__":
	Filename = "Method_Z_Load_Hold_Unload.yaml"
	Init_Pos = [1,2,3]
	Final_Pos = [4,5,6]

	Output_List = Method_to_List(Filename, Init_Pos, Final_Pos)
	print(Output_List)
					
