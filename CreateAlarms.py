#   Copyright:  B&R Industrial Automation
#   Authors:    Adam Sefranek, Michal Vavrik
#   Created:	Oct 26, 2021 1:36 PM

ScriptVersion = "v2.0.1"

# TODO
# Lépe organizovat SetReset alarmů v poli: společné FORy, kde to jde + Flagy pro struktury

#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os, re, sys
import xml.etree.ElementTree as et
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
import pickle

#####################################################################################################################################################
# Global constants
#####################################################################################################################################################
MODE_PREBUILD = 0
MODE_CONFIGURATION = 1
MODE_ERROR = 2
LANGUAGE_C = 0
LANGUAGE_ST = 1
EXTENSIONS = [".c", ".st"]
PERMITTED_TYPES_OF_ARRAY_CONSTANTS = ["USINT", "SINT", "UINT", "INT", "UDINT", "DINT"]

# Validity ranges
RANGE_UDINT = [0, 4294967295]
RANGE_REAL = [-3.4E38, 3.4E38]
RANGE_LREAL = [-1.797E308, 1.797E308]
RANGE_BOOL = ["FALSE", "TRUE", "False", "True", "false", "true"]
RANGE_BEHAVIOR = ["EdgeAlarm", "PersistentAlarm"]
RANGE_DIS_STAT_DYN = ["Disabled", "Static", "Dynamic"]
RANGE_STAT_DYN = ["Static", "Dynamic"]
RANGE_NONE = [None]

# Each key represents allowed alarm property, its value is XML element tag
PROPERTIES = {"Code": {"Tag": "Property", "ID": "Code", "Validity": RANGE_UDINT},
			  "Severity": {"Tag": "Property", "ID": "Severity", "Validity": RANGE_UDINT},
			  "Behavior": {"Tag": "Selector", "ID": "Behavior", "Validity": RANGE_BEHAVIOR},
			  "Behavior.MultipleInstances": {"Tag": "Property", "ID": "MultipleInstances", "Validity": RANGE_BOOL},
			  "Behavior.ReactionUntilAcknowledged": {"Tag": "Property", "ID": "ReactionUntilAcknowledged", "Validity": RANGE_BOOL},
			  "Behavior.Retain": {"Tag": "Property", "ID": "Retain", "Validity": RANGE_BOOL},
			  "Behavior.Asynchronous": {"Tag": "Property", "ID": "Async", "Validity": RANGE_BOOL},
			  "Behavior.DataUpdate": {"Tag": "Group", "ID": "DataUpdate", "Validity": RANGE_NONE},
			  "Behavior.DataUpdate.Activation": {"Tag": "Group", "ID": "Activation", "Validity": RANGE_NONE},
			  "Behavior.DataUpdate.Activation.Timestamp": {"Tag": "Property", "ID": "TimeStamp", "Validity": RANGE_BOOL},
			  "Behavior.DataUpdate.Activation.Snippets": {"Tag": "Property", "ID": "Snippets", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport": {"Tag": "Group", "ID": "Recording", "Validity": RANGE_NONE},
			  "Behavior.HistoryReport.InactiveToActive": {"Tag": "Property", "ID": "InactiveToActive", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.ActiveToInactive": {"Tag": "Property", "ID": "ActiveToInactive", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.UnacknowledgedToAcknowledged": {"Tag": "Property", "ID": "UnacknowledgedToAcknowledged", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.AcknowledgedToUnacknowledged": {"Tag": "Property", "ID": "AcknowledgedToUnacknowledged", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.Update": {"Tag": "Property", "ID": "Update", "Validity": RANGE_BOOL},
			  "Disable": {"Tag": "Property", "ID": "Disable", "Validity": RANGE_BOOL},
			  "AdditionalInformation1": {"Tag": "Property", "ID": "AdditionalInformation1", "Validity": RANGE_NONE},
			  "AdditionalInformation2": {"Tag": "Property", "ID": "AdditionalInformation2", "Validity": RANGE_NONE}}

# Patterns for global types parsing
	# Matches structure definition, returns 2 groups:
	# 1. Name of the structure
	# 2. Members of the structure
PATTERN_STRUCTURE = r"([a-zA-Z0-9_]{1,32})\s{0,}:\s{0,}STRUCT[^\n]{0,}\n([\s\S]*?)\s{0,}END_STRUCT"

	# Matches type members structure definition, returns 10 groups:
	# 1. Name of array variables
	# 2. Start value of array
	# 3. End value of array
	# 4. Type of array variables
	# 5. Descriptions 1 and 2 of array variables
	# 6. Description 2 of array variables
	# 7. Name of non array variables
	# 8. Type of non array variables
	# 9. Descriptions 1 and 2 of non array variables
	# 10. Description 2 of non array variables
PATTERN_MEMBER = r"([a-zA-Z0-9_]{1,32}).*?ARRAY\[([a-zA-Z0-9_-]+)..([a-zA-Z0-9_-]+)\]\s{0,}OF\s{0,}([a-zA-Z0-9_]+)\s{0,};\s{0,}(\(\*.*?\*\)\s*?\(\*(.+?)\*\)\s*?)?\n{0,1}|([a-zA-Z0-9_]{1,32}).*?([a-zA-Z0-9_]{1,32})\s{0,};\s{0,}(\(\*.*?\*\)\s*?\(\*(.+?)\*\)\s*?)?\n{0,1}"

	# Matches Key=Value pairs, returns 2 groups:
	# 1. Key
	# 2. Value
PATTERN_PAIR = r"([a-zA-Z0-9.]+)[ ]*?=[ ]*?([a-zA-Z0-9.:-]+|\"[^;]+\")"

# Patterns for global variables and constants parsing
	# Matches VAR sections, returns 3 groups:
	# 1. VAR RETAIN section
	# 2. VAR CONSTANT section
	# 3. VAR section
PATTERN_VAR_SECTION = r"VAR RETAIN\s{0,}\n\s{0,}([\s\S]*?)\n\s{0,}END_VAR|VAR CONSTANT\s{0,}\n\s{0,}([\s\S]*?)\n\s{0,}END_VAR|VAR[^\na-zA-Z]{0,}\n\s{0,}([\s\S]*?)\n\s{0,}END_VAR"

	# Matches variables in sections, returns 7 groups:
	# 1. Variable name of non array variables
	# 2. UNREPLICABLE tag
	# 3. Type of non array variables
	# 4. Variable name of array variables
	# 5. Start value of array
	# 6. End value of array
	# 7. Type of array variables
PATTERN_VARIABLE = r"([a-zA-Z0-9_]+)\s{0,}:\s{0,}(\{REDUND_UNREPLICABLE\}){0,1}\s{0,}([a-zA-Z0-9_]+)[^;\[\]]{0,};|([a-zA-Z0-9_]+)\s{0,}:\s{0,}ARRAY\[([a-zA-Z0-9_-]+)..([a-zA-Z0-9_-]+)\]\s{0,}OF\s{0,}([a-zA-Z0-9_]+)[^;]{0,};"

	# Matches constants in sections, returns 3 groups:
	# 1. Name
	# 2. Type
	# 3. Value
PATTERN_CONSTANT = r"([a-zA-Z0-9_]+)\s{0,}:\s{0,}([a-zA-Z0-9_]+)\s{0,}:=\s{0,}([^;]+);"

	# Matches inner constants in constants value, returns 1 group:
	# 1. Inner constant name
PATTERN_CONSTANT_VALUE = r"([a-zA-Z][a-zA-Z0-9_]{0,})"

#####################################################################################################################################################
# Class definitions
#####################################################################################################################################################
class Node(object):
	def __init__(self, key, data=None):
		self.key = key
		self.data = data
		self.children = []

	def __iter__(self):
		return iter(self.children)

	def append(self, obj) -> object:
		self.children.append(obj)
		return obj

	def find(self, key):
		return next(iter([node for node in self.children if node.key == key]), None)

#####################################################################################################################################################
# Global functions
#####################################################################################################################################################
# Terminates the script
def TerminateScript():
	# Ouput window message
	print("--------------------------------- End of the script CreateAlarms ---------------------------------")
	sys.exit()

# Debug printing
def DebugPrint(Message, Data):
	if UserData["Debug"]: print(">> " + Message + " >> " + str(Data) + "\n")

# Finds file in directory and subdirectories, returns path to the FIRST found file and terminates script if file does not found and termination is required
# If *.extension FileName input (i.e. *.var) is specified, returns list of all occurrences of this extension
def FindFilePath(SourcePath, FileName, Terminate):
	if "*" in FileName: FilePath = []
	else: FilePath = ""
	EndLoop = False
	for DirPath, DirNames, FileNames in os.walk(SourcePath):
		if "*" in FileName:
			for File in FileNames:
				if File.endswith(FileName[1:]):
					FilePath.append(os.path.join(DirPath, File))
		else:
			for File in FileNames:
				if File == FileName:
					FilePath = os.path.join(DirPath, File)
					EndLoop = True
			if EndLoop:
				break
	if (FilePath == "" or FilePath == []) and Terminate:
		print("Error: File " + FileName + " does not exist.")
		TerminateScript()
	return FilePath

# Checks if file exists and terminates script if not
def IsFile(FilePath):
	if not os.path.isfile(FilePath):
		print("Error: File " + os.path.basename(FilePath) + " does not exist.")
		TerminateScript()
	return True

# Checks if directory exists and terminates script if not
def IsDir(DirPath):
	if not os.path.isdir(DirPath):
		print("Error: Directory " + DirPath + " does not exist.")
		TerminateScript()
	return True

# Get project info (project name, project path, path to logical)
def GetProjectInfo():
	CurrentPath = os.path.dirname(os.path.abspath(__file__))
	if (CurrentPath.find("Logical") == -1):
		print("Error: Directory 'Logical' does not exist.")
		ProjectName = ProjectPath = LogicalPath = ""
	else:
		# Get project path
		ProjectPath = CurrentPath[:CurrentPath.find("Logical") - 1]

		# Get project name
		ProjectName = os.path.basename(ProjectPath)

		# Get logical path
		LogicalPath = CurrentPath[:CurrentPath.find("Logical") + 7]

	return ProjectName, ProjectPath, LogicalPath

# Walk through all variables and data types and create list of alarms
def GetAlarms():
	"""
	Gets Alarm list from all variables and types

	Alarms [{
		Variable: ""
		Array: [Start, End]
		Path: [{
			Name: ""
			Type: ""
			Array: [Start, End]
			Description2: ""
			ParentType: ""
		}]
		Severity: ""
		Properties: [{
				Key: ""
				Value: ""
				Valid: False/True
				Tag: ""
		}]
	}]
	"""

	# Get all valid var and type files
	VarPaths = GetGlobalPaths("var")
	TypePaths = GetGlobalPaths("typ")

	# Get all global variables, constants and types
	GlobalVars, GlobalConsts = GetGlobalVars(VarPaths)
	GlobalTypes = GetGlobalTypes(TypePaths, GlobalConsts)

	# Look for all types with Error/Warning/Info in name
	AlarmTypes = []
	for GlobalType in GlobalTypes:
		if ("Error" in GlobalType["ParentType"]) or ("Warning" in GlobalType["ParentType"]) or ("Info" in GlobalType["ParentType"]):
			AlarmTypes.append(GlobalType["ParentType"])
	
	# Generate all alarm paths
	AlarmPaths = []
	GetPaths(AlarmTypes, GlobalTypes, AlarmPaths, True)
	for AlarmPath in AlarmPaths:
		AlarmPath.reverse()

	# Add global variables to alarm paths
	AlarmPaths = AddVarsToPaths(GlobalVars, GlobalTypes, AlarmPaths)

	# Create alarm list
	Alarms = CreateAlarms(GlobalTypes, AlarmPaths)

	# Alarm paths print
	if UserData["Debug"]:
		print("Paths to alarms:")
		for Index, Alarm in enumerate(Alarms):
			print(str(Index + 1) + ": " + str(PathToAlarm(Alarm)))
		print("\n")

	# Parse properties of alarms
	Alarms = ParseProperties(Alarms)

	DebugPrint("Alarms", Alarms)

	return Alarms

# Get all global paths excluding private files and files from Libraries
def GetGlobalPaths(Extension):
	# Get path to all .Extension files
	GlobalPaths = FindFilePath(LogicalPath, "*." + Extension, True)

	# Remove undesirable Extension files
	PathsToRemove = []
	for GlobalPath in GlobalPaths:
		FileName = os.path.basename(GlobalPath)
		DirName = os.path.dirname(GlobalPath)

		# Remove all "Libraries" files
		if "Libraries" in GlobalPath:
			PathsToRemove.append(GlobalPath)

		# Remove all Private files
		elif os.path.isfile(os.path.join(DirName, "Package.pkg")):
			PkgPath = os.path.join(DirName, "Package.pkg")
			PkgFile = open(PkgPath, "r")
			for Line in PkgFile:
				if (FileName in Line) and ("Private=\"true\"" in Line):
					PathsToRemove.append(GlobalPath)
		else:
			PathsToRemove.append(GlobalPath)

	GlobalPaths = list(set(GlobalPaths) - set(PathsToRemove))
	DebugPrint("All valid ." + Extension + " files", GlobalPaths)

	return GlobalPaths

# Get all global variables from VarPaths
def GetGlobalVars(VarPaths):
	"""
	Parses variables and constants from all valid global .var files.

	GlobalVars [{
		Name: ""
		Type: ""
		Array: [Start, End]
	}]

	GlobalConsts [{
		Name: ""
		Type: ""
		Value: ""
	}]
	"""
	GlobalVars = []
	GlobalConsts = []
	for VarPath in VarPaths:
		VarFile = open(VarPath, "r")
		VarText = VarFile.read()
		VarFile.close()
		VarStructures = re.findall(PATTERN_VAR_SECTION, VarText)
		for VarStructure in VarStructures:
			if (VarStructure[0] != '') or (VarStructure[2] != ''):
				if VarStructure[0] != '':
					Vars = re.findall(PATTERN_VARIABLE, VarStructure[0])
				else:
					Vars = re.findall(PATTERN_VARIABLE, VarStructure[2])
				for Var in Vars:
					if Var[0] != '':
						GlobalVars.append({"Name":Var[0], "Type":Var[2], "Array": ""})
					elif Var[3] != '':
						GlobalVars.append({"Name":Var[3], "Type":Var[6], "Array": [Var[4], Var[5]]})
			elif VarStructure[1] != '':
				Vars = re.findall(PATTERN_CONSTANT, VarStructure[1])
				for Var in Vars:
					if Var[1] in PERMITTED_TYPES_OF_ARRAY_CONSTANTS:
						GlobalConsts.append({"Name":Var[0], "Type":Var[1], "Value": Var[2]})
	
	GlobalConsts = GetConstsValue(GlobalConsts)
	GlobalVars = ReplaceConstsByNums(GlobalVars, GlobalConsts)
	DebugPrint("Global constants", GlobalConsts)
	DebugPrint("Global variables", GlobalVars)

	return GlobalVars, GlobalConsts

# Parse global types
def GetGlobalTypes(TypePaths, GlobalConsts):
	"""
	Parses types from all valid global .typ files.

	GlobalTypes [{
		Name: ""
		Type: ""
		Array: [Start, End]
		Description2: ""
		ParentType: ""
	}]
	"""
	GlobalTypes = []
	for TypePath in TypePaths:
		TypeFile = open(TypePath, "r")
		TypeText = TypeFile.read()
		TypeFile.close()
		TypeStructures = re.findall(PATTERN_STRUCTURE, TypeText)
		for TypeStructure in TypeStructures:
			Members = re.findall(PATTERN_MEMBER, TypeStructure[1])
			for Member in Members:
				if Member[0] != '':
					GlobalTypes.append({"Name": Member[0], "Type": Member[3], "Array": [Member[1], Member[2]], "Description2": Member[5], "ParentType": TypeStructure[0]})
				else:
					GlobalTypes.append({"Name": Member[6], "Type": Member[7], "Array": "", "Description2": Member[9], "ParentType": TypeStructure[0]})
		GlobalTypes = ReplaceConstsByNums(GlobalTypes, GlobalConsts)
	DebugPrint("Global types", GlobalTypes)

	return GlobalTypes

# Get value of all constants
def GetConstsValue(Consts):
	NotDoneConsts = []
	DoneConstsName = []
	DoneConstsValue = []
	for Index, Const in enumerate(Consts):
		try:
			if type(Const["Value"]) == str:
				Consts[Index]["Value"] = int(eval(Const["Value"]))
				DoneConstsName.append(Const["Name"])
				DoneConstsValue.append(Const["Value"])
		except:
			NotDoneConsts.append(Const)
	if NotDoneConsts != []:
		FoundZeroDoneConstants = True
		for Index, Const in enumerate(NotDoneConsts):
			InnerConsts = re.findall(PATTERN_CONSTANT_VALUE, Const["Value"])
			for InnerConst in InnerConsts:
				if InnerConst in DoneConstsName:
					FoundZeroDoneConstants = False
					# Consts[Find index of Const with Name in NotDoneConsts[Index]["Name"]]["Value"] = replace all InnerConst by values
					Consts[next((index for (index, d) in enumerate(Consts) if d["Name"] == NotDoneConsts[Index]["Name"]), None)]["Value"] = re.sub(r"\b%s\b" % InnerConst, str(DoneConstsValue[DoneConstsName.index(InnerConst)]), NotDoneConsts[Index]["Value"])
		if FoundZeroDoneConstants:
			for NotDoneConst in NotDoneConsts:
				InnerConsts = re.findall(PATTERN_CONSTANT_VALUE, NotDoneConst["Value"])
				for InnerConst in InnerConsts:
					if next((index for (index, d) in enumerate(NotDoneConsts) if d["Name"] == InnerConst), None) == None:
						print("Error: Constant " + InnerConst + " cannot be found.")
			TerminateScript()
		GetConstsValue(Consts)
		return Consts
	else:
		return Consts

# Replace list["Array"] defined with onstants by numbers and convert strings to ints
def ReplaceConstsByNums(List, GlobalConsts):
	for Index, Member in enumerate(List):
		if Member["Array"] != "":
			for i in (0,1):
				try:
					List[Index]["Array"][i] = int(Member["Array"][i])
				except:
					try:
						List[Index]["Array"][i] = GlobalConsts[next((index for (index, d) in enumerate(GlobalConsts) if d["Name"] == Member["Array"][i]), None)]["Value"]
					except:
						print("Error: Constant " + Member["Array"][i] + " in array of variable " + Member["Name"] + " cannot be found.")
						TerminateScript()
	return List

# Get all possible paths to alarm types
def GetPaths(AlarmTypes, GlobalTypes, AlarmPaths, FirstTime, Nesting = 0):
	Nesting += 1
	if Nesting >= UserData["MaxNesting"]:
		print("Warning: Recursive nesting in data types.")
		TerminateScript()
	Types = []
	AlarmTypes = list(set(AlarmTypes))
	for GlobalType in GlobalTypes:
		if GlobalType["Type"] in AlarmTypes:
			Types.append(GlobalType["ParentType"])
			if FirstTime:
				AlarmPaths.append([GlobalType])
			else:
				HelpAlarmPaths = []
				for IndexPath, AlarmPath in enumerate(AlarmPaths):
					for IndexMember, PathMember in enumerate(AlarmPath):
						if PathMember["ParentType"] == GlobalType["Type"]:
							if IndexMember == (len(AlarmPaths[IndexPath]) - 1):
								AlarmPaths[IndexPath].append(GlobalType)
							else:
								HelpList = AlarmPaths[IndexPath][:IndexMember + 1]
								HelpList.append(GlobalType)
								DoNotAppend = False
								for Path in AlarmPaths:
									if HelpList == Path[:IndexMember+2]:
										DoNotAppend = True
										break
								if not DoNotAppend:
									if HelpAlarmPaths == []:
										HelpAlarmPaths.append(HelpList)
									else:
										DoNotAppend = False
										for HelpPath in HelpAlarmPaths:
											if HelpList == HelpPath:
												DoNotAppend = True
												break
										if not DoNotAppend:
											HelpAlarmPaths.append(HelpList)
				if HelpAlarmPaths != []:
					for HelpPath in HelpAlarmPaths:
						AlarmPaths.append(HelpPath)
	if Types != []:
		GetPaths(Types, GlobalTypes, AlarmPaths, False, Nesting)

# Add global variables to the beginning of the paths
def AddVarsToPaths(GlobalVars, GlobalTypes, AlarmPaths):
	ExtendedPaths = []
	for GlobalVar in GlobalVars:
		PathsNumber = 0
		for AlarmPath in AlarmPaths:
			for IndexMember, PathMember in enumerate(AlarmPath):
				if GlobalVar["Type"] == PathMember["ParentType"]:
					PathsNumber += 1
					HelpPath = AlarmPath[IndexMember:]
					HelpPath.insert(0, GlobalVar)
					if HelpPath not in ExtendedPaths:
						ExtendedPaths.append(HelpPath)
		if PathsNumber == 0:
			if ("Error" in GlobalVar["Type"]) or ("Warning" in GlobalVar["Type"]) or ("Info" in GlobalVar["Type"]):
				for GlobalType in GlobalTypes:
					if GlobalVar["Type"] == GlobalType["ParentType"]:
						ExtendedPaths.append([GlobalVar])
						break
	return ExtendedPaths

# Create alarm list
def CreateAlarms(GlobalTypes, AlarmPaths):
	Alarms = []
	for AlarmPath in AlarmPaths:
		for GlobalType in GlobalTypes:
			if (GlobalType["ParentType"] == AlarmPath[-1]["Type"]) and (GlobalType["Type"] == "BOOL"):
				if ("Error" in GlobalType["ParentType"]):
					Severity = "Error"
				elif ("Warning" in GlobalType["ParentType"]):
					Severity = "Warning"
				elif ("Info" in GlobalType["ParentType"]):
					Severity = "Info"
				GlobalType["Description2"] = GlobalType["Description2"].replace("Disabled", "0")
				GlobalType["Description2"] = GlobalType["Description2"].replace("Required", "1")
				GlobalType["Description2"] = GlobalType["Description2"].replace("RequiredAfterActive", "2")
				GlobalType["Description2"] = GlobalType["Description2"].replace("RequiredAndResettable", "3")
				Alarms.append({"Variable": GlobalType["Name"], "Array": GlobalType["Array"], "Path": AlarmPath, "Severity": Severity, "Properties": GlobalType["Description2"]})
	return Alarms

# Parse properties of alarms
def ParseProperties(Alarms):
	"""
	Parses Input string and returns list of Alarms.

	Alarm {
		Task: ""
		Type: ""
		Name: ""
		Properties: [
			{
				Key: ""
				Value: ""
				Valid: False/True
				Tag: ""
			}
		]
	}
	"""
	for Member in Alarms:
		Pairs = re.findall(PATTERN_PAIR, Member["Properties"])
		Properties = []

		for Pair in Pairs:
			Key = Pair[0]
			Value = Pair[1]
			
			if Value.startswith("\"") and Value.endswith("\""): 
				Value = Value[1:-1]
			
			if Key in PROPERTIES:
				if "FALSE" in PROPERTIES[Key]["Validity"]:
					Value = Value.upper()
				Valid = Validity(Member["Variable"], Key, Value)
				Properties.append({"Key": Key, "Value": Value, "Valid": Valid, "Tag": PROPERTIES[Key]["Tag"], "ID": PROPERTIES[Key]["ID"]})
			else:
				print("Warning: Property '" + Key + "' of member '" + PathToAlarm(Member) +"' is not valid.")
				Properties.append({"Key": Key, "Value": Value, "Valid": False, "Tag": None, "ID": None})

		if Properties:
			Properties = sorted(Properties, key=lambda d: d["Key"])
			Member["Properties"] = Properties
	
	return Alarms

# Check validity of property value
def Validity(Name, Key, Value):
	Valid = False
	try:
		ValueNotInRangeText = "Warning: Value of property '" + Key + "' of member '" + Name + "' is not in valid range "
		if type(PROPERTIES[Key]["Validity"][0]) == int:
			if int(Value) in range(PROPERTIES[Key]["Validity"][0], PROPERTIES[Key]["Validity"][1]):
				Valid = True
			else:
				print(ValueNotInRangeText + "<" + str(PROPERTIES[Key]["Validity"][0]) + "; " + str(PROPERTIES[Key]["Validity"][1]) + ">")

		elif type(PROPERTIES[Key]["Validity"][0]) == float:
			if (float(Value) >= PROPERTIES[Key]["Validity"][0]) and (float(Value) <= PROPERTIES[Key]["Validity"][1]):
				Valid = True
			else:
				print(ValueNotInRangeText + "<" + str(PROPERTIES[Key]["Validity"][0]) + "; " + str(PROPERTIES[Key]["Validity"][1]) + ">")

		elif type(PROPERTIES[Key]["Validity"][0]) == str:
			if Value in PROPERTIES[Key]["Validity"]:
				Valid = True
			else:
				if "FALSE" in PROPERTIES[Key]["Validity"]: print(ValueNotInRangeText + str(RANGE_BOOL))
				else: print(ValueNotInRangeText + str(PROPERTIES[Key]["Validity"]))
		elif PROPERTIES[Key]["Validity"][0] == None:
			Valid = True

	except:
		print("Warning: Wrong data type of property '" + Key + "' of member '" + Name + "'")

	return Valid

# Create alarm groups
def MpAlarmCreateGroup(Index: int, Name: str, Properties: list) -> et.Element:
	Group = et.Element("Group", {"ID": "["+str(Index)+"]"})
	Message = "{$Alarms/"+Name+"}"
	et.SubElement(Group, "Property", {"ID": "Name", "Value": Name})
	et.SubElement(Group, "Property", {"ID": "Message", "Value": Message})
	Properties = CreateTreeFromProperties(Properties)
	Properties = RemoveInvalidProperties(Properties)
	MpAlarmCreateNodes(Group, Properties)
	return Group

# Tansform alarm list to a tree
def CreateTreeFromProperties(Properties: list) -> Node:
	Tree = Node("Root")
	for Item in Properties:
		Keys = Item["Key"].split(".")
		Last = Keys.pop(-1)
		Parent = Tree
		for Index, Key in enumerate(Keys):
			Child = Parent.find(Key)
			if Child:
				Parent = Child
			else:
				if len(Keys) > 1:
					PropertyName = ".".join(Keys[0:Index+1])
				else:
					PropertyName = Key
				Parent = Parent.append(Node(Key, PROPERTIES[PropertyName]))
		Parent.append(Node(Last, Item))
	return Tree

# Remove invalid properties
def RemoveInvalidProperties(Properties: list) -> list:
	for Index, Item in enumerate(Properties.children):
		if ("Valid" in Item.data and Item.data["Valid"]) or ("Validity" in Item.data and Item.data["Validity"] == RANGE_NONE):
			RemoveInvalidProperties(Item)
		else:
			del(Properties.children[Index])
	return Properties

# Insert new configuration
def MpAlarmCreateNodes(Parent, Properties) -> et.Element:
	for Item in Properties:
		if Item.data:
			Attrib = {"ID": Item.data["ID"]}
			if "Value" in Item.data:
				Attrib["Value"] = Item.data["Value"]
			Element = et.Element(Item.data["Tag"], Attrib)
			MpAlarmCreateNodes(Element, Item)
			Parent.append(Element)
	return Parent

# Function for alarms set/reset text generation
def AlarmSetReset(SetResetText, Alarm, ProgramLanguage):
	AlarmName = ""
	ConfigNameCreation = ["\nbrsmemset(ADR(Name), 0, SIZEOF(Name));"]
	Tabs = "\n"
	NumberOfForLoops = 0
	for IndexMember, PathMember in enumerate(Alarm["Path"]):
		AlarmName += PathMember["Name"]
		if PathMember["Array"] != "":
			NumberOfForLoops += 1
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + PathMember["Name"] + "['));")
			ConfigNameCreation.append("\nbrsmemset(ADR(String), 0, SIZEOF(String));")
			ConfigNameCreation.append("\nbrsitoa(ArrayIndex" + str(NumberOfForLoops) + ", ADR(String));")
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR(String));")
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('].'));")
			AlarmName += "[ArrayIndex" + str(NumberOfForLoops) + "]."
			Tabs = "\n"
			for Index in range(NumberOfForLoops):
				Tabs += "\t"
			SetResetText += Tabs + "FOR ArrayIndex" + str(NumberOfForLoops) + " := " + str(PathMember["Array"][0]) + " TO " + str(PathMember["Array"][1]) + " DO"
		else:
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + PathMember["Name"] + ".'));")
			AlarmName += "."
	AlarmName += Alarm["Variable"]
	if Alarm["Array"] != "":
		NumberOfForLoops += 1
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + Alarm["Variable"] + "['));")
		ConfigNameCreation.append("\nbrsmemset(ADR(String), 0, SIZEOF(String));")
		ConfigNameCreation.append("\nbrsitoa(ArrayIndex" + str(NumberOfForLoops) + ", ADR(String));")
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR(String));")
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR(']'));")
		AlarmName += "[ArrayIndex" + str(NumberOfForLoops) + "]"
		Tabs = "\n"
		for Tab in range(NumberOfForLoops):
			Tabs += "\t"
		SetResetText += Tabs + "FOR ArrayIndex" + str(NumberOfForLoops) + " := " + str(Alarm["Array"][0]) + " TO " + str(Alarm["Array"][1]) + " DO"
	else:
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + Alarm["Variable"] + "'));")
	Tabs += "\t"

	ConfigName = ""
	BeforeStatic = False
	for Line in ConfigNameCreation:
		if "ADR('" in Line:
			if not BeforeStatic:
				ConfigName += Line
			else:
				ConfigName = ConfigName[:ConfigName.rfind("')")] + Line[Line.find("ADR('") + 5:Line.find("')")] + ConfigName[ConfigName.rfind("')"):]
			BeforeStatic = True
		else:
			ConfigName += Line
			BeforeStatic = False

	ConfigName = ConfigName.replace("\n", Tabs + "\t")
	ConfigName = ConfigName.replace("brsstrcat", "brsstrcpy", 1)

	if NumberOfForLoops != 0:
		SetResetText += Tabs + "IF (" + AlarmName + " <> Flag." + AlarmName + ") THEN"
		SetResetText += ConfigName
		SetResetText += Tabs + "\tIF (" + AlarmName + " > Flag." + AlarmName + ") THEN"
		SetResetText += Tabs + "\t\tMpAlarmXSet(gAlarmXCore, Name);"
		SetResetText += Tabs + "\tELSE"
		SetResetText += Tabs + "\t\tMpAlarmXReset(gAlarmXCore, Name);"
		SetResetText += Tabs + "\tEND_IF;"
	else:
		SetResetText += Tabs + "IF (" + AlarmName + " > Flag." + AlarmName + ") THEN"
		SetResetText += Tabs + "\tMpAlarmXSet(gAlarmXCore, '" + AlarmName + "');"
		SetResetText += Tabs + "END_IF;"
		SetResetText += Tabs + "IF (" + AlarmName + " < Flag." + AlarmName + ") THEN"
		SetResetText += Tabs + "\tMpAlarmXReset(gAlarmXCore, '" + AlarmName + "');"
	SetResetText += Tabs + "END_IF;"
	SetResetText += Tabs + "Flag." + AlarmName + "\t:= " + AlarmName + ";"

	for Index in range(NumberOfForLoops):
		Tabs = Tabs[:-1]
		SetResetText += Tabs + "END_FOR;"
	SetResetText += "\n\t"
		
	# Convert ST to C
	if ProgramLanguage == LANGUAGE_C:
		# FOR replacement
		SetResetText = re.sub("([\t]*)FOR ([a-zA-Z0-9_]*) := ([0-9]*) TO ([0-9]*) DO", r"\1for (\2 = \3; \2 <= \4; \2++)\n\1{", SetResetText)
		# IF replacement
		SetResetText = re.sub("([\t]*)IF \(([a-zA-Z0-9_.\[\]]*) ([<>=]*) ([a-zA-Z0-9_.\[\]]*)\) THEN", r"\1if (\2 \3 \4)\n\1{", SetResetText)
		SetResetText = re.sub("END_[a-zA-Z0-9_]*;", "}", SetResetText)
		# END_XXX occurrances
		SetResetText = re.sub("([\t]*)ELSE", r"\1}\n\1else\n\1{", SetResetText)
		# Other
		SetResetText = SetResetText.replace("'", "\"")
		SetResetText = SetResetText.replace(":= ", "= ")
		SetResetText = SetResetText.replace("<>", "!=")
		SetResetText = SetResetText.replace("(gAlarmXCore", "(&gAlarmXCore")
		SetResetText = SetResetText.replace("ADR", "(UDINT)&")
		SetResetText = SetResetText.replace("SIZEOF", "sizeof")

	return SetResetText, NumberOfForLoops

# Prebuild mode function
def Prebuild():

	DebugPrint("User settings", UserData)

	# Update Tmx file
	if UserData["UpdateTmx"]: UpdateTmx()

	# Update mpalarmxcore file
	if UserData["UpdateMpConfig"]: UpdateMpalarmxcore()

	# Update program file
	if UserData["UpdateProgram"]: UpdateProgram()

# Creates all paths to one alarm with all possible array values
def CreateNames(Alarm):
	Names = [""]
	FirstTime = True
	for PathMember in Alarm["Path"]:
		for Index, Name in enumerate(Names):
			if FirstTime:
				Names[Index] += PathMember["Name"]
				FirstTime = False
			else:
				Names[Index] += "." + PathMember["Name"]
		if PathMember["Array"] != "":
			Names = CreateArrays(Names, PathMember["Array"])
	for Index, Name in enumerate(Names):
		Names[Index] += "." + Alarm["Variable"]
	if Alarm["Array"] != "":
		Names = CreateArrays(Names, Alarm["Array"])
	return Names

# Expand paths with arrays
def CreateArrays(Names, Array):
	NewNames = []
	for Name in Names:
		for IndexArray in range(Array[0] - 1, Array[1]):
			NewNames.append(Name + "[" + str(IndexArray + 1) + "]")
	return NewNames

# Return path to alarm with array ranges
def PathToAlarm(Alarm) -> str:
	Path = ""
	for PathMember in Alarm["Path"]:
		Path += PathMember["Name"] + str(PathMember["Array"]) + " > "
	Path += Alarm["Variable"] + str(Alarm["Array"])
	return Path

# Update TMX file
def UpdateTmx():
	#####################################################################################################################################################
	# Update Tmx file
	#####################################################################################################################################################

	# Ouput window message
	print("Updating " + UserData["TmxName"] + ".tmx file...")

	# Get alarm names list from TMX file
	TmxPath = FindFilePath(LogicalPath, UserData["TmxName"] + ".tmx", True)

	TmxTree = et.parse(TmxPath)
	TmxRoot = TmxTree.getroot()

	TmxAlarms = []
	for TmxItem in TmxRoot.findall(".//tu"):
		TmxAlarms.append(TmxItem.attrib["tuid"])
	DebugPrint("Tmx alarms", TmxAlarms)

	# Get alarm names list from Global.typ file
	TypAlarms = []
	for Alarm in Alarms:
		TypAlarms += CreateNames(Alarm)
	DebugPrint("Typ alarms", TypAlarms)

	# Compare alarm names lists
	NewAlarms = [x for x in TypAlarms if x not in set(TmxAlarms)]
	MissingAlarms = [x for x in TmxAlarms if x not in set(TypAlarms)]
	
	DebugPrint("New alarms", NewAlarms)
	DebugPrint("Missing alarms", MissingAlarms)

	# Remove missing alarms
	Parent = TmxRoot.find(".//body")
	for TmxAlarm in Parent.findall(".//tu"):
		if TmxAlarm.get('tuid') in MissingAlarms:
			Parent.remove(TmxAlarm)
	TmxTree.write(TmxPath)

	# Add new alarms
	TmxFile = open(TmxPath, "r")
	TmxText = ""
	for TmxLine in TmxFile:
		if (TmxLine.find("<body />") != -1): # End found
			TmxText += TmxLine[:TmxLine.find(" />")] + ">\n"
			TmxLine = ""
			for NewAlarm in NewAlarms:
				TmxText += "\t<tu tuid=\"" + NewAlarm + "\" />\n"
			TmxText += "</body>\n"
		elif (TmxLine.find("</body>") != -1): # End found
			for NewAlarm in NewAlarms:
				TmxText += "\t<tu tuid=\"" + NewAlarm + "\" />\n"
		TmxText += TmxLine
	TmxFile.close()
	TmxFile = open(TmxPath,"w")
	TmxFile.write(TmxText)
	TmxFile.close()

# Update mpalarmxcore file
def UpdateMpalarmxcore():
	#####################################################################################################################################################
	# Update mpalarmxcore
	#####################################################################################################################################################

	# Ouput window message
	print("Updating " + UserData["MpConfigName"] + ".mpalarmxcore file...")

	# Create path to mpalarmxcore
	MpAlarmPath = FindFilePath(ConfigPath, UserData["MpConfigName"] + ".mpalarmxcore", True)

	# Load file
	IsFile(MpAlarmPath)

	MpAlarmTree = et.parse(MpAlarmPath)
	MpAlarmRoot = MpAlarmTree.getroot()

	# Remove old configuration
	# Parent = MpAlarmRoot.find(".//Group[@ID=\"mapp.AlarmX.Core.Configuration\"]")
	Parent = MpAlarmRoot.find(".//Element[@Type=\"mpalarmxcore\"]")
	for Group in Parent.findall(".//Group[@ID=\"mapp.AlarmX.Core.Configuration\"]"):
		Parent.remove(Group)

	MpAlarmList = et.Element("Group", {"ID": "mapp.AlarmX.Core.Configuration"})

	Index = 0
	for Alarm in Alarms:
		for Name in CreateNames(Alarm):
			Element = MpAlarmCreateGroup(Index, Name, Alarm["Properties"])
			Index += 1
			MpAlarmList.append(Element)

	Parent.append(MpAlarmList)

	# Save file
	MpAlarmTree.write(MpAlarmPath)

# Update program file
def UpdateProgram():
	#####################################################################################################################################################
	# Update alarms program
	#####################################################################################################################################################

	# Detect programming language
	if (FindFilePath(LogicalPath, UserData["ProgramName"] + EXTENSIONS[LANGUAGE_C], False) != ""):
		ProgramLanguage = LANGUAGE_C
	else:
		ProgramLanguage = LANGUAGE_ST
	
	# Ouput window message
	print("Updating " + UserData["ProgramName"] + EXTENSIONS[ProgramLanguage] + " file...")

	# Generate cyclic program
	ProgramPath = FindFilePath(LogicalPath, UserData["ProgramName"] + EXTENSIONS[ProgramLanguage], True)

	# Create whole automatically generated cyclic section and insert it to the file
	ProgramFile = open(ProgramPath, "r")
	ProgramText = ""
	ErrorLastVariableName = ""
	WarningLastVariableName = ""
	InfoLastVariableName = ""
	AutomaticSectionStartFound = False
	InAutomaticSection = False

	if ProgramLanguage == LANGUAGE_C:
		ProgramErrorText = "\t/************************************************************** Errors *************************************************************/"
		ProgramWarningText = "\n\t\n\t/************************************************************* Warnings ************************************************************/"
		ProgramInfoText = "\n\t\n\t/************************************************************** Infos **************************************************************/"
	elif ProgramLanguage == LANGUAGE_ST:
		ProgramErrorText = "\t(************************************************************** Errors *************************************************************)"
		ProgramWarningText = "\n\t\n\t(************************************************************* Warnings ************************************************************)"
		ProgramInfoText = "\n\t\n\t(************************************************************** Infos **************************************************************)"

	MaxNumberOfForLoops = 0
	for ProgramLine in ProgramFile:
		if not InAutomaticSection:
			ProgramText += ProgramLine
		if (ProgramLine.find("// START OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section start
			AutomaticSectionStartFound = True
			InAutomaticSection = True
			for Alarm in Alarms:
				SetResetNotValid = False
				for Property in Alarm["Properties"]:
					if Property["Key"] == "Behavior":
						if ("Monitoring" in Property["Value"]) or not Property["Valid"]:
							SetResetNotValid = True
							break
				if not SetResetNotValid:
					if Alarm["Severity"] == "Error":
						if not(ErrorLastVariableName == Alarm["Path"][0]["Name"]):
							ProgramErrorText += "\n\t// Global variable " + Alarm["Path"][0]["Name"]
						ProgramErrorText, NumberOfForLoops = AlarmSetReset(ProgramErrorText, Alarm, ProgramLanguage)
						ErrorLastVariableName = Alarm["Path"][0]["Name"]
					elif Alarm["Severity"] == "Warning":
						if not(WarningLastVariableName == Alarm["Path"][0]["Name"]):
							ProgramWarningText += "\n\t// Global variable " + Alarm["Path"][0]["Name"]
						ProgramWarningText, NumberOfForLoops = AlarmSetReset(ProgramWarningText, Alarm, ProgramLanguage)
						WarningLastVariableName = Alarm["Path"][0]["Name"]
					elif Alarm["Severity"] == "Info":
						if not(InfoLastVariableName == Alarm["Path"][0]["Name"]):
							ProgramInfoText += "\n\t// Global variable " + Alarm["Path"][0]["Name"]
						ProgramInfoText, NumberOfForLoops = AlarmSetReset(ProgramInfoText, Alarm, ProgramLanguage)
						InfoLastVariableName = Alarm["Path"][0]["Name"]
					
					if NumberOfForLoops > MaxNumberOfForLoops:
						MaxNumberOfForLoops = NumberOfForLoops

			ProgramText += ProgramErrorText + ProgramWarningText + ProgramInfoText

		elif (ProgramLine.find("// END OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section end
			InAutomaticSection = False
			ProgramText += "\n\t\n" + ProgramLine

	ProgramFile.close()
	if not AutomaticSectionStartFound:
		print("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
		TerminateScript()
	elif InAutomaticSection:
		print("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
		TerminateScript()
	else:
		ProgramFile = open(ProgramPath,"w")
		ProgramFile.write(ProgramText)
		ProgramFile.close()
		
	# Check if necessary variables exist and create them if not
	AlarmsVarPath = FindFilePath(os.path.dirname(ProgramPath), UserData["ProgramName"] + ".var", True)
	AlarmsVarFile = open(AlarmsVarPath, "r")
	AlarmsVarContent = AlarmsVarFile.read()
	AlarmsVarText = "\nVAR"
	if not "Flag : FlagType;" in AlarmsVarContent:
		AlarmsVarText += "\n\tFlag : FlagType;"
	if (MaxNumberOfForLoops > 0) and (not "Name : STRING[255];" in AlarmsVarContent):
		AlarmsVarText += "\n\tName : STRING[255];"
	if (MaxNumberOfForLoops > 0) and (not "String : STRING[255];" in AlarmsVarContent):
		AlarmsVarText += "\n\tString : STRING[255];"
	for Index in range(MaxNumberOfForLoops):
		if not ("ArrayIndex" + str(Index + 1) + " : INT;") in AlarmsVarContent:
			AlarmsVarText += "\n\tArrayIndex" + str(Index + 1) + " : INT;"
		
	AlarmsVarText += "\nEND_VAR"
	if AlarmsVarText != "\nVAR\nEND_VAR":
		AlarmsVarFile.close()
		AlarmsVarFile = open(AlarmsVarPath, "a")
		AlarmsVarFile.write(AlarmsVarText)
	AlarmsVarFile.close()

	# Generate Flag type
	AutomaticSectionStartFound = False
	InAutomaticSection = False
	AlarmsTypText = ""
	AlarmsTypPath = FindFilePath(os.path.dirname(ProgramPath), UserData["ProgramName"] + ".typ", True)
	AlarmsTypFile = open(AlarmsTypPath, "r")
	for AlarmsTypLine in AlarmsTypFile:
		if not InAutomaticSection:
			AlarmsTypText += AlarmsTypLine
		if (AlarmsTypLine.find("// START OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section start
			AutomaticSectionStartFound = True
			InAutomaticSection = True

			# Local types generation
			# Get unique paths
			UniquePaths = []
			for Alarm in Alarms:
				if Alarm["Path"] not in UniquePaths:
					UniquePaths.append(Alarm["Path"])

			LocalTypes = ["\nTYPE\n\tFlagType : STRUCT"]
			for UniquePath in UniquePaths:
				for IndexMember, Member in enumerate(UniquePath):
					if IndexMember == 0:
						if not Member["Name"] in LocalTypes[0]:
							if Member["Array"] != "":
								TypeFormat = "ARRAY[" + str(Member["Array"][0]) + ".." + str(Member["Array"][1]) + "]OF "
							else:
								TypeFormat = ""
							if (IndexMember + 1) != len(UniquePath):
								TypeFormat += Member["Type"] + "Flag;"
							else:
								TypeFormat += Member["Type"] + ";"
							LocalTypes[0] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
					else:
						for IndexType, LocalType in enumerate(LocalTypes):
							if Member["Array"] != "":
								TypeFormat = "ARRAY[" + str(Member["Array"][0]) + ".." + str(Member["Array"][1]) + "]OF "
							else:
								TypeFormat = ""
							if (IndexMember + 1) != len(UniquePath):
								TypeFormat += Member["Type"] + "Flag;"
							else:
								TypeFormat += Member["Type"] + ";"
							ParentTypeFormat = Member["ParentType"] + "Flag"
							if ParentTypeFormat + " : STRUCT" in LocalType:
								if not Member["Name"] + " : " + TypeFormat in LocalTypes[IndexType]:
									if Member["Array"] != "":
										LocalTypes[IndexType] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
									else:
										LocalTypes[IndexType] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
								break
							elif (IndexType + 1) == len(LocalTypes):
								LocalTypes.append("\n\t" + ParentTypeFormat + " : STRUCT")
								if Member["Array"] != "":
									LocalTypes[IndexType + 1] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
								else:
									LocalTypes[IndexType + 1] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
								break
			if (len(LocalTypes) == 1) and (LocalTypes[0] == "\nTYPE\n\tFlagType : STRUCT"):
				LocalTypes[0] += "\n\t\tNew_Member : USINT;"
			for LocalType in LocalTypes:
				AlarmsTypText += LocalType + "\n\tEND_STRUCT;"
			AlarmsTypText += "\nEND_TYPE"

		elif (AlarmsTypLine.find("// END OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section end
			InAutomaticSection = False
			AlarmsTypText += "\n\n" + AlarmsTypLine

	AlarmsTypFile.close()
	if not AutomaticSectionStartFound:
		print("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
		TerminateScript()
	elif InAutomaticSection:
		print("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
		TerminateScript()
	else:
		AlarmsTypFile = open(AlarmsTypPath,"w")
		AlarmsTypFile.write(AlarmsTypText)
		AlarmsTypFile.close()

# Configuration: Configuration accepted
def AcceptConfiguration(Config, Debug, UpdateTmx, UpdateMpConfig, UpdateProgram, TmxName, MpConfigName, ProgramName):
	if (TmxName != "") and (MpConfigName != "") and (ProgramName != "") and (MpConfigName != ProgramName):
		UserData["Configuration"] = Config
		UserData["Debug"] = Debug
		UserData["UpdateTmx"] = UpdateTmx
		UserData["UpdateMpConfig"] = UpdateMpConfig
		UserData["UpdateProgram"] = UpdateProgram
		UserData["TmxName"] = TmxName
		UserData["MpConfigName"] = MpConfigName
		UserData["ProgramName"] = ProgramName
		
		with open(UserDataPath, "wb") as CreateAlarmsSettings:
			pickle.dump(UserData, CreateAlarmsSettings)
		sys.exit()

# Configuration mode function
def Configuration():
	# Load configurations name
	ConfigName = []
	ConfigPath = os.path.dirname(os.path.abspath(__file__))
	if (ConfigPath.find("Logical") != -1):
		ConfigPath = ConfigPath[:ConfigPath.find("Logical")]
		for Physical in os.listdir(ConfigPath):
			if (Physical.find("Physical") != -1):
				ConfigPath += "Physical"
				for Config in os.listdir(ConfigPath):
					if not(Config.endswith(".pkg")):
						ConfigName.append(Config)
				break
	
	# Create dialog gui
	Gui = QApplication([])
	Dialog = QDialog()
	Dialog.setStyleSheet("""
		QWidget{
			background-color:qlineargradient(spread:pad, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(0, 0, 0, 255), stop:1 rgba(20, 20, 20, 255));
			color:#cccccc;
			font: 24px \"Bahnschrift SemiLight SemiConde\";
		}
		
		QLabel{
			background-color:transparent;
			color:#888888;
		}

		QLineEdit{
			background-color:#3d3d3d;
			color:#cccccc;
			border:6;
			padding-left:10px;
			height: 50px;
			border-radius:8px;
		}

		QLineEdit:hover{
			color:#cccccc;
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 rgba(55, 55, 55, 255), stop:0.505682 rgba(55, 55, 55, 255), stop:1 rgba(40, 40, 40, 255));
		}

		QComboBox{
			background-color: #3d3d3d;
			color: #cccccc;
			border: none;
			border-radius: 8px;
			padding: 10px;
			position: center;
		}

		QComboBox:hover{
			color:#cccccc;
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 rgba(55, 55, 55, 255), stop:0.505682 rgba(55, 55, 55, 255), stop:1 rgba(40, 40, 40, 255));
		}

		QComboBox::drop-down {
			background-color: transparent;
		}

		QComboBox QAbstractItemView {
			color: #cccccc;
			background-color: #3d3d3d;
		}

		QDialogButtonBox::StandardButton *{
			background-color: #222222;
			width: 180px;
			height: 50px;
		}

		QCheckBox{
			border-style:none;
			background-color:transparent;
		}

		QCheckBox::indicator{
			top: 2px;
			width: 50px;
			height: 50px;
			background-color: #3d3d3d;
			border-radius:8px;
			margin-bottom: 4px;
		}

		QCheckBox::indicator:hover{
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 rgba(55, 55, 55, 255), stop:0.505682 rgba(55, 55, 55, 255), stop:1 rgba(40, 40, 40, 255));
		}

		QCheckBox::indicator:checked{
			background-color:qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #095209, stop:1 #0e780e);
		}

		QPushButton{
			border-style:solid;
			background-color:#3d3d3d;
			color:#cccccc;
			border-radius:8px;
		}

		QPushButton:hover{
			color:#cccccc;
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 rgba(55, 55, 55, 255), stop:0.505682 rgba(55, 55, 55, 255), stop:1 rgba(40, 40, 40, 255));
		}

		QPushButton:pressed{
			background-color:qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 rgba(45, 45, 45, 255), stop:0.505682 rgba(40, 40, 40, 255), stop:1 rgba(45, 45, 45, 255));
			color:#ffffff;
		}

		QPushButton:checked{
			background-color:qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #095209, stop:1 #0e780e);
			color:#ffffff;
		}

		QToolTip{
			font: 16px \"Bahnschrift SemiLight SemiConde\";
			background-color:#eedd22;
			color:#111111;
			border: solid black 1px;
		}

		QGroupBox{
			border-left: 2px solid;
			border-right: 2px solid;
			border-bottom: 2px solid;
			border-color: #362412;
			margin-top: 38px;
			border-radius: 0px;
		}

		QGroupBox::title{
			subcontrol-origin: margin;
			subcontrol-position: top center;
			padding: 5px 8000px;
			background-color: #362412;
		}
		"""
		)

	# Dialog.setWindowFlag(Qt.FramelessWindowHint) # Borderless window
	Dialog.setWindowTitle(" ")
	Dialog.setGeometry(0, 0, 500, 300)

	# Center window
	Rectangle = Dialog.frameGeometry()
	CenterPoint = QDesktopWidget().availableGeometry().center()
	Rectangle.moveCenter(CenterPoint)
	Dialog.move(Rectangle.topLeft())

	# Creating a group box
	FormGroupBox = QGroupBox("Welcome to CreateAlarms configuration", parent=Dialog)

	# Creating a form layout
	Layout = QFormLayout(parent=FormGroupBox)
	Layout.setHorizontalSpacing(20)

	#####################################################################################################################################################
	# Update alarms program
	#####################################################################################################################################################

	# Configuration selection
	ConfigComboBox = QComboBox()
	ConfigComboBox.addItems(ConfigName)
	ConfigComboBox.setToolTip("Select configuration with .mpalarmxcore file")
	ConfigComboBox.setCurrentText(UserData["Configuration"])
	ConfigLabel = QLabel("Select configuration")
	ConfigLabel.setToolTip("Select configuration with .mpalarmxcore file")
	Layout.addRow(ConfigLabel, ConfigComboBox)

	# Debug option
	DebugPushButton = QPushButton("DEBUG")
	DebugPushButton.setToolTip("Turns on printing of debug messages")
	DebugPushButton.setCheckable(True)
	DebugPushButton.setChecked(UserData["Debug"])
	DebugPushButton.setFixedHeight(50)
	DebugLabel = QLabel("Turn on debugging")
	DebugLabel.setToolTip("Turns on printing of debug messages")
	Layout.addRow(DebugLabel, DebugPushButton)

	# Tmx name
	TmxNameLineEdit = QLineEdit()
	TmxNameLineEdit.setToolTip("Name of the tmx file without .tmx extension")
	TmxNameLineEdit.setText(UserData["TmxName"])
	TmxNameLineEdit.setFixedHeight(50)
	TmxNameLabel = QLabel("Tmx name")
	TmxNameLabel.setToolTip("Name of the tmx file without .tmx extension")
	TmxExtensionLabel = QLabel(".tmx")
	TmxExtensionLabel.setToolTip("Name of the tmx file without .tmx extension")
	TmxNameRow = QHBoxLayout()
	TmxNameRow.addWidget(TmxNameLineEdit)
	TmxNameRow.addSpacing(10)
	TmxNameRow.addWidget(TmxExtensionLabel)
	Layout.addRow(TmxNameLabel, TmxNameRow)

	# MpConfig name
	MpConfigNameLineEdit = QLineEdit()
	MpConfigNameLineEdit.setToolTip("Name of the MpConfig file without .mpalarmxcore extension (cannot be same as program name)")
	MpConfigNameLineEdit.setText(UserData["MpConfigName"])
	MpConfigNameLineEdit.setFixedHeight(50)
	MpConfigNameLabel = QLabel("MpConfig name")
	MpConfigNameLabel.setToolTip("Name of the MpConfig file without .mpalarmxcore extension (cannot be same as program name)")
	MpConfigExtensionLabel = QLabel(".mpalarmxcore")
	MpConfigExtensionLabel.setToolTip("Name of the MpConfig file without .mpalarmxcore extension (cannot be same as program name)")
	MpConfigNameRow = QHBoxLayout()
	MpConfigNameRow.addWidget(MpConfigNameLineEdit)
	MpConfigNameRow.addSpacing(10)
	MpConfigNameRow.addWidget(MpConfigExtensionLabel)
	Layout.addRow(MpConfigNameLabel, MpConfigNameRow)

	# Program name
	ProgramNameLineEdit = QLineEdit()
	ProgramNameLineEdit.setToolTip("Name of the program file without .st/.c extension (cannot be same as MpConfig name)")
	ProgramNameLineEdit.setText(UserData["ProgramName"])
	ProgramNameLineEdit.setFixedHeight(50)
	ProgramNameLabel = QLabel("Program name")
	ProgramNameLabel.setToolTip("Name of the program file without .st/.c extension (cannot be same as MpConfig name)")
	ProgramExtensionLabel = QLabel(".st/.c")
	ProgramExtensionLabel.setToolTip("Name of the program file without .st/.c extension (cannot be same as MpConfig name)")
	ProgramNameRow = QHBoxLayout()
	ProgramNameRow.addWidget(ProgramNameLineEdit)
	ProgramNameRow.addSpacing(10)
	ProgramNameRow.addWidget(ProgramExtensionLabel)
	Layout.addRow(ProgramNameLabel, ProgramNameRow)

	# Sections update
	UpdateTmxCheckBox = QCheckBox("Update TMX")
	UpdateTmxCheckBox.setToolTip("The script will update the TMX file every build")
	UpdateTmxCheckBox.setFixedHeight(50)
	UpdateTmxCheckBox.setChecked(UserData["UpdateTmx"])
	UpdateMpConfigCheckBox = QCheckBox("Update MpConfig")
	UpdateMpConfigCheckBox.setToolTip("The script will update the MpAlarmXCore file every build")
	UpdateMpConfigCheckBox.setFixedHeight(50)
	UpdateMpConfigCheckBox.setChecked(UserData["UpdateMpConfig"])
	UpdateProgramCheckBox = QCheckBox("Update Set/Reset")
	UpdateProgramCheckBox.setToolTip("The script will update the .st/.c program file every build")
	UpdateProgramCheckBox.setFixedHeight(50)
	UpdateProgramCheckBox.setChecked(UserData["UpdateProgram"])
	UpdateSectionRow = QHBoxLayout()
	UpdateSectionRow.addWidget(UpdateTmxCheckBox)
	UpdateSectionRow.addSpacing(10)
	UpdateSectionRow.addWidget(UpdateMpConfigCheckBox)
	UpdateSectionRow.addSpacing(10)
	UpdateSectionRow.addWidget(UpdateProgramCheckBox)
	Layout.addRow(UpdateSectionRow)

	# Creating a dialog button for ok and cancel
	FormButtonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

	# Version label
	VersionLabel = QLabel("ⓘ " + ScriptVersion, parent=FormButtonBox)
	VersionLabel.move(0, 10)
	VersionLabel.setStyleSheet("QLabel{font: 20px \"Bahnschrift SemiLight SemiConde\"; background-color: transparent;} QToolTip{background-color:#eedd22;}")
	VersionLabel.setToolTip("""To get more information about each row, hold the pointer on its label.
	\nSupport contacts
	michal.vavrik@br-automation.com
	adam.sefranek@br-automation.com
	\nVersion 2.0.1
	- Once nested alarms path bug fixed
	- Supported properties change
	- Print of used configuration
	\nVersion 2.0.0
	- New system of finding alarm paths
	- Support of arrays (also defined by constants)
	\nVersion 1.2.0
	- Configuration of sections to update
	- Configuration of TMX, MpConfig and program name
	- Properties validity
	- Strings must be in quotation marks
	\nVersion 1.1.0
	- Bug with default alarm behavior fixed
	- Behavior.Monitoring.MonitoredPV bug fixed
	- Tags are taken from the graphics editor
	- Monitoring alarm types have no longer Set and Reset in the Alarms program
	- Path to user data changed to AppData\Roaming\BR\Scripts\CreateAlarms\\
	- Error mode added
	\nVersion 1.0.0
	- Script creation
	- Basic functions implemented""")

	# Adding actions for form
	FormButtonBox.accepted.connect(lambda: AcceptConfiguration(ConfigComboBox.currentText(), DebugPushButton.isChecked(), UpdateTmxCheckBox.isChecked(), UpdateMpConfigCheckBox.isChecked(), UpdateProgramCheckBox.isChecked(), TmxNameLineEdit.text(), MpConfigNameLineEdit.text(), ProgramNameLineEdit.text()))
	FormButtonBox.rejected.connect(Dialog.reject)
	TmxNameLineEdit.textChanged.connect(lambda: TextInputCheck(TmxNameLineEdit))
	MpConfigNameLineEdit.textChanged.connect(lambda: TextInputCheck(MpConfigNameLineEdit, ProgramNameLineEdit))
	ProgramNameLineEdit.textChanged.connect(lambda: TextInputCheck(ProgramNameLineEdit, MpConfigNameLineEdit))

	# Creating a vertical layout
	MainLayout = QVBoxLayout()

	# Adding form group box to the layout
	MainLayout.addWidget(FormGroupBox)

	# Adding button box to the layout
	MainLayout.addWidget(FormButtonBox)
	
	# Setting lay out
	Dialog.setLayout(MainLayout)

	# Show dialog
	Dialog.show()
	Gui.exec()

# Text inputs condition check
def TextInputCheck(TextInput1: QLineEdit, TextInput2: QLineEdit = None):
	if (TextInput1.text() == ""):
		TextInput1.setStyleSheet("QLineEdit{background:#661111;}")
	else:
		TextInput1.setStyleSheet("")

	if TextInput2 != None:
		if (TextInput2.text() == ""):
			TextInput2.setStyleSheet("QLineEdit{background:#661111;}")
		else:
			TextInput2.setStyleSheet("")

		if (TextInput1.text() == TextInput2.text()):
			TextInput1.setStyleSheet("QLineEdit{background:#661111;}")
			TextInput2.setStyleSheet("QLineEdit{background:#661111;}")

# Logical folder not found -> show error message
def LogicalNotFoundMessage():
	# Create dialog gui
	Gui = QApplication([])
	Dialog = QDialog()
	Dialog.setStyleSheet("""
		QWidget{
			background-color:qlineargradient(spread:pad, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(0, 0, 0, 255), stop:1 rgba(20, 20, 20, 255));
			color:#cccccc;
			font: 24px \"Bahnschrift SemiLight SemiConde\";
		}
		
		QLabel{
			background-color:transparent;
			color:#bb2222;
			padding: 10px;
		}""")
	Dialog.setWindowTitle("Error")
	Dialog.setGeometry(0, 0, 500, 120)

	# Center window
	Rectangle = Dialog.frameGeometry()
	CenterPoint = QDesktopWidget().availableGeometry().center()
	Rectangle.moveCenter(CenterPoint)
	Dialog.move(Rectangle.topLeft())

	# Creating a group box
	ErrorLabel = QLabel("Directory Logical not found. Please copy this script to the LogicalView of your project.", parent=Dialog)
	ErrorLabel.setGeometry(0, 0, 500, 120)
	ErrorLabel.setWordWrap(True)
	ErrorLabel.setAlignment(QtCore.Qt.AlignTop)
	
	# Show dialog
	Dialog.show()
	Gui.exec()

#####################################################################################################################################################
# Main
#####################################################################################################################################################

# Get project info
ProjectName, ProjectPath, LogicalPath = GetProjectInfo()

# Script mode decision
if LogicalPath == "":
	# Logical path not found
	RunMode = MODE_ERROR

elif "-prebuild" in sys.argv:
	# Argument -prebuild found
	RunMode = MODE_PREBUILD

else:
	# Argument -prebuild not found
	RunMode = MODE_CONFIGURATION

if not RunMode == MODE_ERROR:
	# Get path to user data
	UserDataPath = os.path.join(os.getenv("APPDATA"), "BR", "Scripts", "CreateAlarms", ProjectName)
	if not os.path.isdir(os.path.dirname(UserDataPath)):
		os.makedirs(os.path.dirname(UserDataPath))

	# Load user data
	try:
		with open(UserDataPath, "rb") as CreateAlarmsSettings:
			UserData = pickle.load(CreateAlarmsSettings)
	except:
		UserData = {"Configuration":"", "Debug": False, "UpdateTmx": True, "UpdateMpConfig": True, "UpdateProgram": True, "TmxName": "Alarms", "MpConfigName": "AlarmsCfg", "ProgramName": "Alarms", "MaxNesting": 15}

	if (len(UserData) != 9):
		UserData = {"Configuration":"", "Debug": False, "UpdateTmx": True, "UpdateMpConfig": True, "UpdateProgram": True, "TmxName": "Alarms", "MpConfigName": "AlarmsCfg", "ProgramName": "Alarms", "MaxNesting": 15}

	# Get selected config path
	ConfigPath = os.path.join(ProjectPath, "Physical", UserData["Configuration"])

# Run respective script mode
if RunMode == MODE_PREBUILD:
	
	# Ouput window message
	print("----------------------- Beginning of the script CreateAlarms " + ScriptVersion + " -----------------------")
	if UserData["Configuration"] != "":
		UsedConfiguration = UserData["Configuration"]
	else:
		UsedConfiguration = FindFilePath(ConfigPath, UserData["MpConfigName"] + ".mpalarmxcore", True)
		UsedConfiguration = UsedConfiguration[UsedConfiguration.find("Physical") + 9:]
		UsedConfiguration = UsedConfiguration[:UsedConfiguration.find("\\")]
	print("Used configuration: " + UsedConfiguration)

	# Get alarms from global variables and types
	Alarms = GetAlarms()

	Prebuild()

	# Ouput window message
	print("--------------------------------- End of the script CreateAlarms ---------------------------------")

elif RunMode == MODE_CONFIGURATION:
	Configuration()

elif RunMode == MODE_ERROR:
	LogicalNotFoundMessage()
