#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os
import re
import sys
import xml.etree.ElementTree as et

# What will be in configuration GUI:
# Language selection
# Configuration selection
# Option to run script

#####################################################################################################################################################
# Debug mode (debug print)
#####################################################################################################################################################
DEBUG = True

#####################################################################################################################################################
# List of possible properties
#####################################################################################################################################################
KEYS = ["Code", "Severity", "Behavior"]

#####################################################################################################################################################
# Open Global.typ file
#####################################################################################################################################################
LogicalPath = os.path.dirname(os.path.abspath(__file__))
if (LogicalPath.find("Logical") == -1):
    sys.exit("Directory 'Logical' does not exist.")

LogicalPath = LogicalPath[:LogicalPath.find("Logical") + 7]
TypPath = os.path.join(LogicalPath, "Global.typ")

if not os.path.isfile(TypPath):
    sys.exit("File 'Global.typ' does not exist.")

with open(TypPath, "r") as f:
    TypContent = f.read()

#####################################################################################################################################################
# Parse data from Global.typ file
#####################################################################################################################################################

# Matches structure definition, returns three groups:
# 1. Name of the structure
# 2. Structure suffix (Error, Info, Warning)
# 3. Members of the structure
PatternStructure = r"g([a-zA-Z0-9]{1,10})(Error|Info|Warning)Type[^\n]+\n([\s\S]*?)END_STRUCT"

# Matches BOOL structure members with Description[2] filled in, returns two groups:
# 1. Name of the member
# 2. Content of Description[2]
PatternMember = r"([a-zA-Z0-9_]{1,32}).*?BOOL[\s;]*?\(\*.*?\*\)\s*?\(\*(.+?)\*\)\s*?(?:\(.*?)?[ ]*?\n"

# Matches Key=Value pairs, returns two groups:
# 1. Key
# 2. Value
PatternPair = r"([a-zA-Z0-9]+)[ ]*?=[ ]*?([a-zA-Z0-9]+)"

# Alarm {
#     Task: ""
#     Type: ""
#     Name: ""
#     Properties: [
#         {
#           Key: ""
#           Value: ""
#           Valid: False/True
#         }
#     ]
# }
Alarms = []
Structures = re.findall(PatternStructure, TypContent)
for Structure in Structures:
    Members = re.findall(PatternMember, Structure[2])
    for Member in Members:
        Pairs = re.findall(PatternPair, Member[1])
        Properties = []
        for Pair in Pairs:
            try:
                Key = Pair[0].capitalize()
                Index = KEYS.index(Key)
                Properties.append({"Key": Key, "Value": Pair[1], "Valid": True})
            except ValueError:
                print("Warning: Key '"+Key+"' of member 'g"+Structure[0]+Structure[1]+"Type."+Member[0]+"' is not valid.")
        if Properties:
            Alarms.append({"Task": Structure[0], "Type": Structure[1], "Name": Member[0], "Properties": Properties})

if DEBUG: print(Alarms)

# Example
# for Alarm in Alarms:
#     print(Alarm["Name"])
#     for Property in Alarm["Properties"]:
#         print(Property["Key"],Property["Value"])

#####################################################################################################################################################
# Debug print
#####################################################################################################################################################
if DEBUG:
    print("Total properties: "+str(len(Properties)))
    for Item in Properties:
        print(Item)

#####################################################################################################################################################
# Validity of dependencies
#####################################################################################################################################################

# No validity of dependencies with basic properties

#####################################################################################################################################################
# Get alarm names list of TMX file
#####################################################################################################################################################
TmxPath = os.path.join(LogicalPath, "Alarms", "Alarms.tmx")
if not os.path.isfile(TmxPath):
    sys.exit("File 'Alarms.tmx' does not exist.")

TmxTree = et.parse(TmxPath)
TmxRoot = TmxTree.getroot()

TmxAlarms = []
for TmxItem in TmxRoot.findall(".//tu"):
    TmxAlarms.append(TmxItem.attrib["tuid"])

if DEBUG: print("Tmx alamrs: " + str(TmxAlarms))

#####################################################################################################################################################
# Get alarm names from Global.typ with unique alarm name
#####################################################################################################################################################
# Get all alarm names
TypAlarms = []
for Alarm in Alarms:
    TypAlarms.append("g" + Alarm["Task"] + "." + Alarm["Type"] + "." + Alarm["Name"])

if DEBUG: print("Typ alarms: " + str(TypAlarms))

#####################################################################################################################################################
# Compare alarm names
#####################################################################################################################################################
NewAlarms = list(set(TypAlarms) - set(TmxAlarms))
MissingAlarms = list(set(TmxAlarms) - set(TypAlarms))
if DEBUG:
    print("New alarms are: " + str(NewAlarms))
    print("Missing alarms are: " + str(MissingAlarms))

#####################################################################################################################################################
# Update TMX file
#####################################################################################################################################################
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

#TmxTree = et.parse(TmxPath)
#TmxRoot = TmxTree.getroot()
#TmxBody = TmxRoot.find(".//body")
#print(TmxBody)

#####################################################################################################################################################
# Update mpalarmxcore
#####################################################################################################################################################

# Create path to mpalarmxcore
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

CpuPath = os.path.join(ConfigPath, ConfigName[0])
for Cpu in os.listdir(CpuPath):
    TmpPath = os.path.join(CpuPath, Cpu)
    if os.path.isdir(os.path.join(CpuPath, Cpu)):
        CpuPath = os.path.join(CpuPath, Cpu)

MpAlarmPath = os.path.join(CpuPath, "mappServices", "Alarms.mpalarmxcore")

# Load file
if not os.path.isfile(MpAlarmPath):
    sys.exit("File 'Alarms.mpalarmxcore' does not exist.")

MpAlarmTree = et.parse(MpAlarmPath)
MpAlarmRoot = MpAlarmTree.getroot()

# Remove old configuration
Parent = MpAlarmRoot.find(".//Group[@ID=\"mapp.AlarmX.Core.Configuration\"]")
for Group in Parent.findall("Group"): # TODO pokud je vložený čistý MpAlarmXCore, tak v něm není element Group a tohle nic nenajde
    print(Group.attrib)
    Parent.remove(Group)

# Insert new configuration
#

# Save file
MpAlarmTree.write(MpAlarmPath)

#####################################################################################################################################################
# Update alarms program TODO psát chybu, když nenajde sekci pro autogen, přidat typy Flag
#####################################################################################################################################################
LANGUAGE_C = 0
LANGUAGE_ST = 1
Extensions = [".c", ".st"]
ProgramLanguage = LANGUAGE_ST
if ProgramLanguage == LANGUAGE_ST:
    ProgramPath = os.path.join(LogicalPath, "Alarms", "Alarms" + Extensions[ProgramLanguage])
    if not os.path.isfile(ProgramPath):
        sys.exit("File 'Alarms" + Extensions[ProgramLanguage] + "' does not exist.")
    else:
        # Add new alarms
        ProgramFile = open(ProgramPath, "r")
        ProgramText = ""
        ErrorLastTaskName = ""
        ProgramErrorSetText = "\t(************************************************************ Error set ************************************************************)"
        ProgramErrorResetText = "\n\n\t(*********************************************************** Error reset ***********************************************************)"
        WarningLastTaskName = ""
        ProgramWarningSetText = "\n\n\t(*********************************************************** Warning set ***********************************************************)"
        ProgramWarningResetText = "\n\n\t(********************************************************** Warning reset **********************************************************)"
        InfoLastTaskName = ""
        ProgramInfoSetText = "\n\n\t(************************************************************* Info set ************************************************************)"
        ProgramInfoResetText = "\n\n\t(************************************************************ Info reset ***********************************************************)"
        InAutomaticSection = False
        for ProgramLine in ProgramFile:
            if not InAutomaticSection:
                ProgramText += ProgramLine
            if (ProgramLine.find("// START OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section start
                InAutomaticSection = True
                for Alarm in Alarms:
                    AlarmVariable = "g" + Alarm["Task"] + "." + Alarm["Type"] + "." + Alarm["Name"]
                    if Alarm["Type"] == "Error":
                        if not(ErrorLastTaskName == Alarm["Task"]):
                            ProgramErrorSetText += "\n\n\t// Task " + Alarm["Task"]
                            ProgramErrorResetText += "\n\n\t// Task " + Alarm["Task"]
                        ProgramErrorSetText += """
	IF (""" + AlarmVariable + """ >  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXSet(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
                        ProgramErrorResetText += """
	IF (""" + AlarmVariable + """ <  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXReset(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
                        ErrorLastTaskName = Alarm["Task"]
                    elif Alarm["Type"] == "Warning":
                        if not(WarningLastTaskName == Alarm["Task"]):
                            ProgramWarningSetText += "\n\n\t// Task " + Alarm["Task"]
                            ProgramWarningResetText += "\n\n\t// Task " + Alarm["Task"]
                        ProgramWarningSetText += """
	IF (""" + AlarmVariable + """ >  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXSet(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
                        ProgramWarningResetText += """
	IF (""" + AlarmVariable + """ <  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXReset(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
                        WarningLastTaskName = Alarm["Task"]
                    elif Alarm["Type"] == "Info":
                        if not(InfoLastTaskName == Alarm["Task"]):
                            ProgramInfoSetText += "\n\n\t// Task " + Alarm["Task"]
                            ProgramInfoResetText += "\n\n\t// Task " + Alarm["Task"]
                        ProgramInfoSetText += """
	IF (""" + AlarmVariable + """ >  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXSet(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
                        ProgramInfoResetText += """
	IF (""" + AlarmVariable + """ <  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXReset(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
                        InfoLastTaskName = Alarm["Task"]

                ProgramText += ProgramErrorSetText + ProgramErrorResetText + ProgramWarningSetText + ProgramWarningResetText + ProgramInfoSetText + ProgramInfoResetText

            elif (ProgramLine.find("// END OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section end
                InAutomaticSection = False
                ProgramText += "\n\n" + ProgramLine
        
        ProgramFile.close()
        ProgramFile = open(ProgramPath,"w")
        ProgramFile.write(ProgramText)
        ProgramFile.close()