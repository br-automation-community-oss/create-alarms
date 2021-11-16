#   Copyright:  B&R Industrial Automation
#   Authors:    Adam Sefranek, Michal Vavrik
#   Created:	Oct 26, 2021 1:36 PM
#   Version:	1.2.0

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

# Validity ranges
RANGE_UDINT = [0, 4294967295]
RANGE_REAL = [-3.4E38, 3.4E38]
RANGE_LREAL = [-1.797E308, 1.797E308]
RANGE_BOOL = ["FALSE", "TRUE", "False", "True", "false", "true"] # TODO Je možné všechny tyto možnosti zapsat do .mpalarmxcore?
RANGE_BEHAVIOR = ["EdgeAlarm", "PersistentAlarm", "LevelMonitoring"]
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
              "Behavior.Monitoring": {"Tag": "Group", "ID": "Monitoring", "Validity": RANGE_NONE},
              "Behavior.Monitoring.MonitoredPV": {"Tag": "Property", "ID": "MonitoredPV", "Validity": RANGE_NONE},
              "Behavior.Monitoring.LowLimit": {"Tag": "Selector", "ID": "LowLimitEnable", "Validity": RANGE_DIS_STAT_DYN},
              "Behavior.Monitoring.LowLimit.Limit": {"Tag": "Property", "ID": "Limit", "Validity": RANGE_LREAL},
              "Behavior.Monitoring.LowLimit.LimitPV": {"Tag": "Property", "ID": "LimitPV", "Validity": RANGE_NONE},
              "Behavior.Monitoring.LowLimit.LimitText": {"Tag": "Property", "ID": "LimitText", "Validity": RANGE_NONE},
              "Behavior.Monitoring.HighLimit": {"Tag": "Selector", "ID": "HighLimitEnable", "Validity": RANGE_DIS_STAT_DYN},
              "Behavior.Monitoring.HighLimit.Limit": {"Tag": "Property", "ID": "Limit", "Validity": RANGE_LREAL},
              "Behavior.Monitoring.HighLimit.LimitPV": {"Tag": "Property", "ID": "LimitPV", "Validity": RANGE_NONE},
              "Behavior.Monitoring.HighLimit.LimitText": {"Tag": "Property", "ID": "LimitText", "Validity": RANGE_NONE},
              "Behavior.Monitoring.Settings": {"Tag": "Selector", "ID": "Settings", "Validity": RANGE_STAT_DYN},
              "Behavior.Monitoring.Settings.Delay": {"Tag": "Property", "ID": "Delay", "Validity": RANGE_REAL},
              "Behavior.Monitoring.Settings.Hysteresis": {"Tag": "Selector", "ID": "Hysteresis", "Validity": RANGE_LREAL},
              "Behavior.Monitoring.Settings.DelayPV": {"Tag": "Property", "ID": "DelayPV", "Validity": RANGE_NONE},
              "Behavior.Monitoring.Settings.HysteresisPV": {"Tag": "Property", "ID": "HysteresisPV", "Validity": RANGE_NONE},
              "Disable": {"Tag": "Property", "ID": "Disable", "Validity": RANGE_BOOL},
              "AdditionalInformation1": {"Tag": "Property", "ID": "AdditionalInformation1", "Validity": RANGE_NONE},
              "AdditionalInformation2": {"Tag": "Property", "ID": "AdditionalInformation2", "Validity": RANGE_NONE}}

# Matches structure definition, returns three groups:
# 1. Name of the structure
# 2. Structure suffix (Error, Info, Warning)
# 3. Members of the structure
PATTERN_STRUCTURE = r"g([a-zA-Z0-9]{1,10})(Error|Info|Warning)Type[^\n]+\n([\s\S]*?)END_STRUCT"

# Matches BOOL structure members with Description[2] filled in, returns two groups:
# 1. Name of the member
# 2. Content of Description[2]
PATTERN_MEMBER = r"([a-zA-Z0-9_]{1,32}).*?BOOL[\s;]*?\(\*.*?\*\)\s*?\(\*(.+?)\*\)\s*?(?:\(.*?)?[ ]*?\n"

# Matches Key=Value pairs, returns two groups:
# 1. Key
# 2. Value
# TODO U stringů vracet hodnoty bez uvozovek
PATTERN_PAIR = r"([a-zA-Z0-9.]+)[ ]*?=[ ]*?([a-zA-Z0-9.:-]+|\"[^;]+\")"

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
# Finds file in directory and subdirectories, returns path to the first found file and terminates script if file does not found and termination is required
def FindFilePath(SourcePath, FileName, Terminate):
    FilePath = ""
    for DirPath, DirNames, FileNames in os.walk(SourcePath):
        for FileNam in [File for File in FileNames if File == FileName]:
            FilePath = (os.path.join(DirPath, FileNam))
    if FilePath == "" and Terminate:
        print("Error: File " + FileName + " does not exist.")
        sys.exit()
    return FilePath

# Checks if file exists and terminates script if not
def IsFile(FilePath):
    if not os.path.isfile(FilePath):
        print("Error: File " + os.path.basename(FilePath) + " does not exist.")
        sys.exit()
    return True

# Checks if directory exists and terminates script if not
def IsDir(DirPath):
    if not os.path.isdir(DirPath):
        print("Error: Directory " + DirPath + " does not exist.")
        sys.exit()
    return True
    
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

def MpAlarmCreateGroup(Index: int, Alarm: dict) -> et.Element:
    Group = et.Element("Group", {"ID": "["+str(Index)+"]"})
    Name = "g"+Alarm["Task"]+"."+Alarm["Type"]+"."+Alarm["Name"]
    Message = "{$Alarms/"+Name+"}"
    et.SubElement(Group, "Property", {"ID": "Name", "Value": Name})
    et.SubElement(Group, "Property", {"ID": "Message", "Value": Message})
    Properties = CreateTreeFromProperties(Alarm["Properties"])
    MpAlarmCreateNodes(Group, Properties)
    return Group

# Function for alarms set/reset text generation
def AlarmSetReset(VariableSetText, VariableResetText, AlarmVariable, ProgramLanguage):
    if ProgramLanguage == LANGUAGE_C:
        VariableSetText += """
	if (""" + AlarmVariable + """ >  Flag.""" + AlarmVariable + """)
	{
		MpAlarmXSet(&gAlarmXCore, \"""" + AlarmVariable + """\");
	}"""
        VariableResetText += """
	if (""" + AlarmVariable + """ <  Flag.""" + AlarmVariable + """)
	{
		MpAlarmXReset(&gAlarmXCore, \"""" + AlarmVariable + """\");
	};"""
    elif ProgramLanguage == LANGUAGE_ST:
        VariableSetText += """
	IF (""" + AlarmVariable + """ >  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXSet(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
        VariableResetText += """
	IF (""" + AlarmVariable + """ <  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXReset(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
    return VariableSetText, VariableResetText

# Get path to Logical directory
def GetLogicalPath():
    LogicalPath = os.path.dirname(os.path.abspath(__file__))
    if (LogicalPath.find("Logical") == -1):
        print("Error: Directory 'Logical' does not exist.")
        LogicalPath = ""
    else:
        LogicalPath = LogicalPath[:LogicalPath.find("Logical") + 7]
    return LogicalPath

# Get alarms
def GetTypAlarms():
    #####################################################################################################################################################
    # Open Global.typ file
    #####################################################################################################################################################
    TypPath = os.path.join(LogicalPath, "Global.typ")
    IsFile(TypPath)

    with open(TypPath, "r") as f:
        TypContent = f.read()
        f.close()
    
    #####################################################################################################################################################
    # Parse data from Global.typ file
    #####################################################################################################################################################
    Alarms = GetAlarms(TypContent)
    return Alarms

# Check properties validity
def Validity():
    #####################################################################################################################################################
    # Validity of dependencies
    #####################################################################################################################################################
    # TODO
    pass

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

    if UserData["Debug"]: print("Tmx alamrs: " + str(TmxAlarms))

    # Get alarm names list from Global.typ file
    TypAlarms = []
    for Alarm in Alarms:
        TypAlarms.append("g" + Alarm["Task"] + "." + Alarm["Type"] + "." + Alarm["Name"])

    if UserData["Debug"]: print("Typ alarms: " + str(TypAlarms))

    # Compare alarm names lists
    NewAlarms = list(set(TypAlarms) - set(TmxAlarms))
    MissingAlarms = list(set(TmxAlarms) - set(TypAlarms))
    if UserData["Debug"]:
        print("New alarms are: " + str(NewAlarms))
        print("Missing alarms are: " + str(MissingAlarms))

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

# Parse TYP file and return list of alarms
def GetAlarms(Input: str) -> list:
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
    Alarms = []
    Structures = re.findall(PATTERN_STRUCTURE, Input)
    for Structure in Structures:
        Members = re.findall(PATTERN_MEMBER, Structure[2])
        for Member in Members:
            Pairs = re.findall(PATTERN_PAIR, Member[1])
            Properties = []
            for Pair in Pairs:
                if Pair[0] in PROPERTIES:
                    Valid = False
                    try:
                        ValueNotInRangeText = "Warning: Value of property '" + Pair[0] + "' of member 'g" + Structure[0] + Structure[1] + "Type." + Member[0] + "' is not in valid range "
                        if type(PROPERTIES[Pair[0]]["Validity"][0]) == int:
                            if int(Pair[1]) in range(PROPERTIES[Pair[0]]["Validity"][0], PROPERTIES[Pair[0]]["Validity"][1]):
                                Valid = True
                            else:
                                print(ValueNotInRangeText + "<" + str(PROPERTIES[Pair[0]]["Validity"][0]) + "; " + str(PROPERTIES[Pair[0]]["Validity"][1]) + ">")

                        elif type(PROPERTIES[Pair[0]]["Validity"][0]) == float:
                            if (float(Pair[1]) >= PROPERTIES[Pair[0]]["Validity"][0]) and (float(Pair[1]) <= PROPERTIES[Pair[0]]["Validity"][1]):
                                Valid = True
                            else:
                                print(ValueNotInRangeText + "<" + str(PROPERTIES[Pair[0]]["Validity"][0]) + "; " + str(PROPERTIES[Pair[0]]["Validity"][1]) + ">")

                        elif type(PROPERTIES[Pair[0]]["Validity"][0]) == str:
                            if Pair[1] in PROPERTIES[Pair[0]]["Validity"]:
                                Valid = True
                            else:
                                if "FALSE" in PROPERTIES[Pair[0]]["Validity"]: print(ValueNotInRangeText + str(RANGE_BOOL))
                                else: print(ValueNotInRangeText + str(PROPERTIES[Pair[0]]["Validity"]))
                        elif PROPERTIES[Pair[0]]["Validity"][0] == None:
                            Valid = True
                        else:
                            Valid = False
                    except:
                        print("Warning: Wrong data type of property '" + Pair[0] + "' of member 'g" + Structure[0] + Structure[1] + "Type." + Member[0] + "'")

                    Properties.append({"Key": Pair[0], "Value": Pair[1], "Valid": Valid, "Tag": PROPERTIES[Pair[0]]["Tag"], "ID": PROPERTIES[Pair[0]]["ID"]})
                else:
                    print("Warning: Property '" + Pair[0] + "' of member 'g" + Structure[0] + Structure[1] + "Type." + Member[0]+"' is not valid.")
            if Properties:
                Properties = sorted(Properties, key=lambda d: d["Key"])
                Alarms.append({"Task": Structure[0], "Type": Structure[1], "Name": Member[0], "Properties": Properties})
    if UserData["Debug"]: print(Alarms)
    return Alarms

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

# Update mpalarmxcore file
def UpdateMpalarmxcore():
    #####################################################################################################################################################
    # Update mpalarmxcore
    #####################################################################################################################################################

    # Ouput window message
    print("Updating " + UserData["MpConfigName"] + ".mpalarmxcore file...")

    # Create path to mpalarmxcore
    ConfigDir = os.path.dirname(os.path.abspath(__file__))
    ConfigDir = ConfigDir[:ConfigDir.find("Logical")]
    ConfigDir = os.path.join(ConfigDir, "Physical", UserData["Configuration"])
    MpAlarmPath = FindFilePath(ConfigDir, UserData["MpConfigName"] + ".mpalarmxcore", True)
    # Load file
    IsFile(MpAlarmPath)

    MpAlarmTree = et.parse(MpAlarmPath)
    MpAlarmRoot = MpAlarmTree.getroot()

    # Remove old configuration
    # Parent = MpAlarmRoot.find(".//Group[@ID=\"mapp.AlarmX.Core.Configuration\"]")
    Parent = MpAlarmRoot.find(".//Element[@Type=\"mpalarmxcore\"]")
    for Group in Parent.findall(
            ".//Group[@ID=\"mapp.AlarmX.Core.Configuration\"]"):
        Parent.remove(Group)

    MpAlarmList = et.Element("Group", {"ID": "mapp.AlarmX.Core.Configuration"})

    # TODO: přidávat property jen když je Property["Valid"] == True
    for Index, Alarm in enumerate(Alarms):
        Element = MpAlarmCreateGroup(Index, Alarm)
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
    ErrorLastTaskName = ""
    WarningLastTaskName = ""
    InfoLastTaskName = ""
    AutomaticSectionStartFound = False
    InAutomaticSection = False

    if ProgramLanguage == LANGUAGE_C:
        ProgramErrorSetText = "\t/************************************************************ Error set ************************************************************/"
        ProgramErrorResetText = "\n\t\n\t/*********************************************************** Error reset ***********************************************************/"
        ProgramWarningSetText = "\n\t\n\t/*********************************************************** Warning set ***********************************************************/"
        ProgramWarningResetText = "\n\t\n\t/********************************************************** Warning reset **********************************************************/"
        ProgramInfoSetText = "\n\t\n\t/************************************************************* Info set ************************************************************/"
        ProgramInfoResetText = "\n\t\n\t/************************************************************ Info reset ***********************************************************/"
        FlagsText = "\n\t\n\t/********************************************************** Flags handling *********************************************************/"
    elif ProgramLanguage == LANGUAGE_ST:
        ProgramErrorSetText = "\t(************************************************************ Error set ************************************************************)"
        ProgramErrorResetText = "\n\t\n\t(*********************************************************** Error reset ***********************************************************)"
        ProgramWarningSetText = "\n\t\n\t(*********************************************************** Warning set ***********************************************************)"
        ProgramWarningResetText = "\n\t\n\t(********************************************************** Warning reset **********************************************************)"
        ProgramInfoSetText = "\n\t\n\t(************************************************************* Info set ************************************************************)"
        ProgramInfoResetText = "\n\t\n\t(************************************************************ Info reset ***********************************************************)"
        FlagsText = "\n\t\n\t(********************************************************** Flags handling *********************************************************)"

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
                    AlarmVariable = "g" + Alarm["Task"] + "." + Alarm["Type"] + "." + Alarm["Name"]
                    if Alarm["Type"] == "Error":
                        if not(ErrorLastTaskName == Alarm["Task"]):
                            ProgramErrorSetText += "\n\t\n\t// Task " + Alarm["Task"]
                            ProgramErrorResetText += "\n\t\n\t// Task " + Alarm["Task"]
                        ProgramErrorSetText, ProgramErrorResetText = AlarmSetReset(ProgramErrorSetText, ProgramErrorResetText, AlarmVariable, ProgramLanguage)
                        ErrorLastTaskName = Alarm["Task"]
                    elif Alarm["Type"] == "Warning":
                        if not(WarningLastTaskName == Alarm["Task"]):
                            ProgramWarningSetText += "\n\t\n\t// Task " + Alarm["Task"]
                            ProgramWarningResetText += "\n\t\n\t// Task " + Alarm["Task"]
                        ProgramWarningSetText, ProgramWarningResetText = AlarmSetReset(ProgramWarningSetText, ProgramWarningResetText, AlarmVariable, ProgramLanguage)
                        WarningLastTaskName = Alarm["Task"]
                    elif Alarm["Type"] == "Info":
                        if not(InfoLastTaskName == Alarm["Task"]):
                            ProgramInfoSetText += "\n\t\n\t// Task " + Alarm["Task"]
                            ProgramInfoResetText += "\n\t\n\t// Task " + Alarm["Task"]
                        ProgramInfoSetText, ProgramInfoResetText = AlarmSetReset(ProgramInfoSetText, ProgramInfoResetText, AlarmVariable, ProgramLanguage)
                        InfoLastTaskName = Alarm["Task"]

                    if not "g" + Alarm["Task"] + "." + Alarm["Type"] in FlagsText:
                        if ProgramLanguage == LANGUAGE_C:
                            FlagsText += "\n\tFlag.g" + Alarm["Task"] + "." + Alarm["Type"] + "\t= g" + Alarm["Task"] + "." + Alarm["Type"] + ";"
                        elif ProgramLanguage == LANGUAGE_ST:
                            FlagsText += "\n\tFlag.g" + Alarm["Task"] + "." + Alarm["Type"] + "\t:= g" + Alarm["Task"] + "." + Alarm["Type"] + ";"

            ProgramText += ProgramErrorSetText + ProgramErrorResetText + ProgramWarningSetText + ProgramWarningResetText + ProgramInfoSetText + ProgramInfoResetText + FlagsText

        elif (ProgramLine.find("// END OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section end
            InAutomaticSection = False
            ProgramText += "\n\t\n" + ProgramLine

    ProgramFile.close()
    if not AutomaticSectionStartFound:
        print("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
        sys.exit()
    elif InAutomaticSection:
        print("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
        sys.exit()
    else:
        ProgramFile = open(ProgramPath,"w")
        ProgramFile.write(ProgramText)
        ProgramFile.close()
        
    # Check if Flag variable exists and create it if not
    AlarmsVarPath = FindFilePath(os.path.dirname(ProgramPath), UserData["ProgramName"] + ".var", True)
    AlarmsVarFile = open(AlarmsVarPath, "r")
    if not "Flag : FlagType;" in AlarmsVarFile.read():
        AlarmsVarFile.close()
        AlarmsVarFile = open(AlarmsVarPath, "a")
        AlarmsVarFile.write("\nVAR\n\tFlag : FlagType;\nEND_VAR")
    AlarmsVarFile.close()

    # Generate Flag type
    AutomaticSectionStartFound = False
    InAutomaticSection = False
    AlarmsTypText = ""
    AuxiliaryText = ""
    AlarmsTypPath = FindFilePath(os.path.dirname(ProgramPath), UserData["ProgramName"] + ".typ", True)
    AlarmsTypFile = open(AlarmsTypPath, "r")
    for AlarmsTypLine in AlarmsTypFile:
        if not InAutomaticSection:
            AlarmsTypText += AlarmsTypLine
        if (AlarmsTypLine.find("// START OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section start
            AlarmsTypText += "\nTYPE\n\tFlagType : STRUCT"
            AutomaticSectionStartFound = True
            InAutomaticSection = True
            for Alarm in Alarms:
                if not "g" + Alarm["Task"] in AlarmsTypText:
                    if AuxiliaryText != "":
                        AuxiliaryText += "\n\tEND_STRUCT;\n\tg" + Alarm["Task"] + "FlagType : STRUCT"
                    else:
                        AuxiliaryText = "\n\tg" + Alarm["Task"] + "FlagType : STRUCT"
                    AlarmsTypText += "\n\t\tg" + Alarm["Task"] + " : " + "g" + Alarm["Task"] + "FlagType;"
                if not "g" + Alarm["Task"] + Alarm["Type"] + "Type" in AuxiliaryText:
                    AuxiliaryText += "\n\t\t" + Alarm["Type"] + " : g" + Alarm["Task"] + Alarm["Type"] + "Type;"
            AlarmsTypText += "\n\tEND_STRUCT;" + AuxiliaryText + "\n\tEND_STRUCT;" + "\nEND_TYPE"

        elif (AlarmsTypLine.find("// END OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section end
            InAutomaticSection = False
            AlarmsTypText += "\n\n" + AlarmsTypLine

    AlarmsTypFile.close()
    if not AutomaticSectionStartFound:
        print("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
        sys.exit()
    elif InAutomaticSection:
        print("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
        sys.exit()
    else:
        AlarmsTypFile = open(AlarmsTypPath,"w")
        AlarmsTypFile.write(AlarmsTypText)
        AlarmsTypFile.close()

# Prebuild mode function
def Prebuild():

    if UserData["Debug"]: print("User settings:" + str(UserData))

    # Update Tmx file
    if UserData["UpdateTmx"]: UpdateTmx()

    # Update mpalarmxcore file
    if UserData["UpdateMpConfig"]: UpdateMpalarmxcore()

    # Update program file
    if UserData["UpdateProgram"]: UpdateProgram()

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
    VersionLabel = QLabel("ⓘ v1.2.0", parent=FormButtonBox)
    VersionLabel.move(0, 10)
    VersionLabel.setStyleSheet("QLabel{font: 20px \"Bahnschrift SemiLight SemiConde\"; background-color: transparent;} QToolTip{background-color:#eedd22;}")
    VersionLabel.setToolTip("""To get more information about each row, hold the pointer on its label.
	\nVersion 1.2.0:
	- Configuration of sections to update
	- Configuration of TMX, MpConfig and program name
	- Properties validity
	- Strings must be in quotation marks
	\nVersion 1.1.0:
	- Bug with default alarm behavior fixed
	- Behavior.Monitoring.MonitoredPV bug fixed
	- Tags are taken from the graphics editor
	- Monitoring alarm types have no longer Set and Reset in the Alarms program
	- Path to user data changed to AppData\Roaming\BR\Scripts\CreateAlarms\\
	- Error mode added
	\nVersion 1.0.0:
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

# Get path to Logical directory
LogicalPath = GetLogicalPath()

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
    # Get project name
    ProjectPath = LogicalPath[:LogicalPath.find("Logical") - 1]
    ProjectName = os.path.basename(ProjectPath)

    # Get path to user data
    UserDataPath = os.path.join(os.getenv("APPDATA"), "BR", "Scripts", "CreateAlarms", ProjectName)
    if not os.path.isdir(os.path.dirname(UserDataPath)):
        os.makedirs(os.path.dirname(UserDataPath))

    # Load user data
    try:
        with open(UserDataPath, "rb") as CreateAlarmsSettings:
            UserData = pickle.load(CreateAlarmsSettings)
    except:
        UserData = {"Configuration":"", "Debug": False, "UpdateTmx": True, "UpdateMpConfig": True, "UpdateProgram": True, "TmxName": "Alarms", "MpConfigName": "AlarmsCfg", "ProgramName": "Alarms"}

    if (len(UserData) != 8):
        UserData = {"Configuration":"", "Debug": False, "UpdateTmx": True, "UpdateMpConfig": True, "UpdateProgram": True, "TmxName": "Alarms", "MpConfigName": "AlarmsCfg", "ProgramName": "Alarms"}

# Run respective script mode
if RunMode == MODE_PREBUILD:
    
    # Ouput window message
    print("----------------------------- Beginning of the script CreateAlarms -----------------------------")

    # Get alarms from global types
    Alarms = GetTypAlarms()

    # Check properties validity
    Validity()

    Prebuild()
    
    # Ouput window message
    print("--------------------------------- End of the script CreateAlarms ---------------------------------")

elif RunMode == MODE_CONFIGURATION:
    Configuration()

elif RunMode == MODE_ERROR:
    LogicalNotFoundMessage()
