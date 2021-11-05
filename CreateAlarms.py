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
# Finds file in directory and subdirectories and returns path to first found file


def FindFilePath(SourcePath, FileName):
    FilePath = ""
    for DirPath, DirNames, FileNames in os.walk(SourcePath):
        for FileNam in [File for File in FileNames if File == FileName]:
            FilePath = (os.path.join(DirPath, FileNam))
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
TmxPath = FindFilePath(LogicalPath, "Alarms.tmx")
IsFile(TmxPath)

TmxTree = et.parse(TmxPath)
TmxRoot = TmxTree.getroot()

TmxAlarms = []
for TmxItem in TmxRoot.findall(".//tu"):
    TmxAlarms.append(TmxItem.attrib["tuid"])

if DEBUG:
    print("Tmx alarms: " + str(TmxAlarms))

# Get alarm names list from Global.typ file
TypAlarms = []
for Alarm in Alarms:
    TypAlarms.append("g" + Alarm["Task"] + "." + Alarm["Type"] + "." +
                     Alarm["Name"])

if DEBUG:
    print("Typ alarms: " + str(TypAlarms))

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
    if (TmxLine.find("<body />") != -1):  # End found
        TmxText += TmxLine[:TmxLine.find(" />")] + ">\n"
        TmxLine = ""
        for NewAlarm in NewAlarms:
            TmxText += "\t<tu tuid=\"" + NewAlarm + "\" />\n"
        TmxText += "</body>\n"
    elif (TmxLine.find("</body>") != -1):  # End found
        for NewAlarm in NewAlarms:
            TmxText += "\t<tu tuid=\"" + NewAlarm + "\" />\n"
    TmxText += TmxLine
TmxFile.close()
TmxFile = open(TmxPath, "w")
TmxFile.write(TmxText)
TmxFile.close()

#TmxTree = et.parse(TmxPath)
#TmxRoot = TmxTree.getroot()
#TmxBody = TmxRoot.find(".//body")
# print(TmxBody)

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
                if not (Config.endswith(".pkg")):
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
# Update alarms program TODO přidat datové typy Flag, udělat jazyk C
#####################################################################################################################################################


def AlarmSetReset(VariableSetText, VariableResetText, AlarmVariable):
    VariableSetText += """
	IF (""" + AlarmVariable + """ >  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXSet(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
    VariableResetText += """
	IF (""" + AlarmVariable + """ <  Flag.""" + AlarmVariable + """) THEN
		MpAlarmXReset(gAlarmXCore, '""" + AlarmVariable + """');
	END_IF;"""
    return VariableSetText, VariableResetText


LANGUAGE_C = 0
LANGUAGE_ST = 1
Extensions = [".c", ".st"]
ProgramLanguage = LANGUAGE_ST
if ProgramLanguage == LANGUAGE_ST:
    ProgramPath = FindFilePath(LogicalPath,
                               "Alarms" + Extensions[ProgramLanguage])
    if IsFile(ProgramPath):
        # Create whole automatically generated section and insert it to the file
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
        AutomaticSectionStartFound = False
        InAutomaticSection = False
        AutomaticSectionEndFound = False
        for ProgramLine in ProgramFile:
            if not InAutomaticSection:
                ProgramText += ProgramLine
            if (ProgramLine.find("// START OF AUTOMATIC CODE GENERATION //") !=
                    -1):  # Automatic generation section start
                AutomaticSectionStartFound = True
                InAutomaticSection = True
                for Alarm in Alarms:
                    AlarmVariable = "g" + Alarm["Task"] + "." + Alarm[
                        "Type"] + "." + Alarm["Name"]
                    if Alarm["Type"] == "Error":
                        if not (ErrorLastTaskName == Alarm["Task"]):
                            ProgramErrorSetText += "\n\n\t// Task " + Alarm[
                                "Task"]
                            ProgramErrorResetText += "\n\n\t// Task " + Alarm[
                                "Task"]
                        ProgramErrorSetText, ProgramErrorResetText = AlarmSetReset(
                            ProgramErrorSetText, ProgramErrorResetText,
                            AlarmVariable)
                        ErrorLastTaskName = Alarm["Task"]
                    elif Alarm["Type"] == "Warning":
                        if not (WarningLastTaskName == Alarm["Task"]):
                            ProgramWarningSetText += "\n\n\t// Task " + Alarm[
                                "Task"]
                            ProgramWarningResetText += "\n\n\t// Task " + Alarm[
                                "Task"]
                        ProgramWarningSetText, ProgramWarningResetText = AlarmSetReset(
                            ProgramWarningSetText, ProgramWarningResetText,
                            AlarmVariable)
                        WarningLastTaskName = Alarm["Task"]
                    elif Alarm["Type"] == "Info":
                        if not (InfoLastTaskName == Alarm["Task"]):
                            ProgramInfoSetText += "\n\n\t// Task " + Alarm[
                                "Task"]
                            ProgramInfoResetText += "\n\n\t// Task " + Alarm[
                                "Task"]
                        ProgramInfoSetText, ProgramInfoResetText = AlarmSetReset(
                            ProgramInfoSetText, ProgramInfoResetText,
                            AlarmVariable)
                        InfoLastTaskName = Alarm["Task"]

                ProgramText += ProgramErrorSetText + ProgramErrorResetText + ProgramWarningSetText + \
                    ProgramWarningResetText + ProgramInfoSetText + ProgramInfoResetText

            elif (ProgramLine.find("// END OF AUTOMATIC CODE GENERATION //") !=
                  -1):  # Automatic generation section end
                AutomaticSectionEndFound = True
                InAutomaticSection = False
                ProgramText += "\n\n" + ProgramLine

        ProgramFile.close()
        if not AutomaticSectionStartFound:
            sys.exit("Start of automatically generated section in Alarms" +
                     Extensions[ProgramLanguage] + " not found.")
        elif not AutomaticSectionEndFound:
            sys.exit("End of automatically generated section in Alarms" +
                     Extensions[ProgramLanguage] + " not found.")
        else:
            ProgramFile = open(ProgramPath, "w")
            ProgramFile.write(ProgramText)
            ProgramFile.close()
