#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os, sys
import xml.etree.ElementTree as et
from GetAlarms import GetAlarms, CreateTreeFromProperties

# What will be in configuration GUI:
# Language selection
# Configuration selection
# Option to run script

#####################################################################################################################################################
# Debug mode (debug print)
#####################################################################################################################################################
DEBUG = False

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
        sys.exit("File " + FileName + " does not exist.")
    return FilePath

# Checks if file exists and terminates script if not
def IsFile(FilePath):
    if not os.path.isfile(FilePath):
        sys.exit("File " + os.path.basename(FilePath) + " does not exist.")
    return True

# Checks if directory exists and terminates script if not
def IsDir(DirPath):
    if not os.path.isdir(DirPath):
        sys.exit("Directory " + DirPath + " does not exist.")
    return True


#####################################################################################################################################################
# Open Global.typ file
#####################################################################################################################################################
LogicalPath = os.path.dirname(os.path.abspath(__file__))
if (LogicalPath.find("Logical") == -1):
    sys.exit("Directory 'Logical' does not exist.")

LogicalPath = LogicalPath[:LogicalPath.find("Logical") + 7]
TypPath = os.path.join(LogicalPath, "Global.typ")
IsFile(TypPath)

with open(TypPath, "r") as f:
    TypContent = f.read()

#####################################################################################################################################################
# Parse data from Global.typ file
#####################################################################################################################################################
Alarms = GetAlarms(TypContent)

#####################################################################################################################################################
# Validity of dependencies
#####################################################################################################################################################

# No validity of dependencies with basic properties

#####################################################################################################################################################
# Update TMX file
#####################################################################################################################################################

# Get alarm names list from TMX file
TmxPath = FindFilePath(LogicalPath, "Alarms.tmx", True)

TmxTree = et.parse(TmxPath)
TmxRoot = TmxTree.getroot()

TmxAlarms = []
for TmxItem in TmxRoot.findall(".//tu"):
    TmxAlarms.append(TmxItem.attrib["tuid"])

if DEBUG: print("Tmx alamrs: " + str(TmxAlarms))

# Get alarm names list from Global.typ file
TypAlarms = []
for Alarm in Alarms:
    TypAlarms.append("g" + Alarm["Task"] + "." + Alarm["Type"] + "." + Alarm["Name"])

if DEBUG: print("Typ alarms: " + str(TypAlarms))

# Compare alarm names lists
NewAlarms = list(set(TypAlarms) - set(TmxAlarms))
MissingAlarms = list(set(TmxAlarms) - set(TypAlarms))
if DEBUG:
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

# Insert new configuration


def MpAlarmCreateNodes(Parent, Properties) -> et.Element:
    for Item in Properties:
        if Item.data:
            Attrib = {"ID": Item.key}
            if Item.data["Value"]:
                Attrib["Value"] = Item.data["Value"]
            Element = et.Element(Item.data["Tag"], Attrib)
            MpAlarmCreateNodes(Element, Item)
            Parent.append(Element)
    return Parent


def MpAlarmCreateGroup(Index: int, Alarm: dict) -> et.Element:
    Group = et.Element("Group", {"ID": "["+str(Index)+"]"})
    Name = "g"+Alarm["Task"]+"."+Alarm["Type"]+"."+Alarm["Name"]
    Message = "{$User/Alarms/"+Name+"}"
    et.SubElement(Group, "Property", {"ID": "Name", "Value": Name})
    et.SubElement(Group, "Property", {"ID": "Message", "Value": Message})
    Properties = CreateTreeFromProperties(Alarm["Properties"])
    MpAlarmCreateNodes(Group, Properties)
    return Group


for Index, Alarm in enumerate(Alarms):
    Element = MpAlarmCreateGroup(Index, Alarm)
    MpAlarmList.append(Element)

Parent.append(MpAlarmList)

# Save file
MpAlarmTree.write(MpAlarmPath)

#####################################################################################################################################################
# Update alarms program
#####################################################################################################################################################

# Constants
LANGUAGE_C = 0
LANGUAGE_ST = 1
EXTENSIONS = [".c", ".st"]

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

# Detect programming language
if (FindFilePath(LogicalPath, "Alarms" + EXTENSIONS[LANGUAGE_C], False) != ""):
    ProgramLanguage = LANGUAGE_C
else:
    ProgramLanguage = LANGUAGE_ST

# Generate cyclic program
ProgramPath = FindFilePath(LogicalPath, "Alarms" + EXTENSIONS[ProgramLanguage], True)

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
    sys.exit("Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
elif InAutomaticSection:
    sys.exit("End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
else:
    ProgramFile = open(ProgramPath,"w")
    ProgramFile.write(ProgramText)
    ProgramFile.close()
    
# Check if Flag variable exists and create it if not
AlarmsVarPath = FindFilePath(os.path.dirname(ProgramPath), "Alarms.var", True)
AlarmsVarFile = open(AlarmsVarPath, "r")
if not "Flag : FlagType;" in AlarmsVarFile.read():
    AlarmsVarFile.close()
    AlarmsVarFile = open(AlarmsVarPath, "a")
    AlarmsVarFile.write("VAR\n\tFlag : FlagType;\nEND_VAR")
AlarmsVarFile.close()

# Generate Flag type
AutomaticSectionStartFound = False
InAutomaticSection = False
AlarmsTypText = ""
AuxiliaryText = ""
AlarmsTypPath = FindFilePath(os.path.dirname(ProgramPath), "Alarms.typ", True)
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
    sys.exit("Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
elif InAutomaticSection:
    sys.exit("End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
else:
    AlarmsTypFile = open(AlarmsTypPath,"w")
    AlarmsTypFile.write(AlarmsTypText)
    AlarmsTypFile.close()