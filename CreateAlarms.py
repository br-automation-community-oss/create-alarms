#   Copyright:  B&R Industrial Automation
#   Authors:    Adam Sefranek, Michal Vavrik
#   Created:	Oct 26, 2021 1:36 PM
#   Version:	1.0.0

#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os, re, sys
import xml.etree.ElementTree as et
from PyQt5.QtWidgets import *
import pickle

#####################################################################################################################################################
# Global constants
#####################################################################################################################################################
MODE_PREBUILD = 0
MODE_GUI = 1
LANGUAGE_C = 0
LANGUAGE_ST = 1
EXTENSIONS = [".c", ".st"]

# Each key represents allowed alarm property, its value is XML element tag
PROPERTIES = {"Code": "Property", "Severity": "Property", "Behavior": "Selector",
              "Behavior.Retain": "Property", "Behavior.Asynchronous": "Property",
              "Behavior.Monitoring": "Group", "Behavior.Monitoring.MonitoredPV": "Property",
              "Behavior.Monitoring.LowLimitEnable": "Selector", "Behavior.Monitoring.LowLimitEnable.Limit": "Property",
              "Behavior.Monitoring.HighLimitEnable": "Selector", "Behavior.Monitoring.HighLimitEnable.Limit": "Property"}

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
PATTERN_PAIR = r"([a-zA-Z0-9.]+)[ ]*?=[ ]*?([a-zA-Z0-9]+)"

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

    def append(self, obj):
        self.children.append(obj)

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
        sys.exit()
    LogicalPath = LogicalPath[:LogicalPath.find("Logical") + 7]
    return LogicalPath

# Get alarms
def GetTypAlarms(LogicalPath):
    #####################################################################################################################################################
    # Open Global.typ file
    #####################################################################################################################################################
    TypPath = os.path.join(LogicalPath, "Global.typ")
    IsFile(TypPath)

    with open(TypPath, "r") as f:
        TypContent = f.read()

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
    # No validity of dependencies with basic properties
    pass

# Update TMX file
def UpdateTmx(LogicalPath, Alarms):
    #####################################################################################################################################################
    # Update Tmx file
    #####################################################################################################################################################

    # Ouput window message
    print("Updating TMX file...")

    # Get alarm names list from TMX file
    TmxPath = FindFilePath(LogicalPath, "Alarms.tmx", True)

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
                    Properties.append(
                        {"Key": Pair[0], "Value": Pair[1], "Valid": True, "Tag": PROPERTIES[Pair[0]]})
                else:
                    print("Warning: Key '"+Pair[0]+"' of member 'g"+Structure[0] +
                          Structure[1]+"Type."+Member[0]+"' is not valid.")
            if Properties:
                Properties = sorted(Properties, key=lambda d: d["Key"])
                Alarms.append(
                    {"Task": Structure[0], "Type": Structure[1], "Name": Member[0], "Properties": Properties})
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
                Parent.append(Node(Key))
        Parent.append(Node(Last, Item))
    return Tree

# Update mpalarmxcore file
def UpdateMpalarmxcore(Alarms):
    #####################################################################################################################################################
    # Update mpalarmxcore
    #####################################################################################################################################################

    # Ouput window message
    print("Updating AlarmsCfg.mpalarmxcore file...")

    # Create path to mpalarmxcore
    ConfigDir = os.path.dirname(os.path.abspath(__file__))
    ConfigDir = ConfigDir[:ConfigDir.find("Logical")]
    ConfigDir = os.path.join(ConfigDir, "Physical", UserData["Configuration"])
    MpAlarmPath = FindFilePath(ConfigDir, "AlarmsCfg.mpalarmxcore", True)
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

    for Index, Alarm in enumerate(Alarms):
        Element = MpAlarmCreateGroup(Index, Alarm)
        MpAlarmList.append(Element)

    Parent.append(MpAlarmList)

    # Save file
    MpAlarmTree.write(MpAlarmPath)

# Update program file
def UpdateProgram(LogicalPath, Alarms):
    #####################################################################################################################################################
    # Update alarms program
    #####################################################################################################################################################

    # Ouput window message
    print("Updating Alarms program...")

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
        print("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
        sys.exit()
    elif InAutomaticSection:
        print("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
        sys.exit()
    else:
        AlarmsTypFile = open(AlarmsTypPath,"w")
        AlarmsTypFile.write(AlarmsTypText)
        AlarmsTypFile.close()

# GUI: Configuration accepted
def AcceptConfiguration(Config, Debug):
    UserData["Configuration"] = Config
    UserData["Debug"] = Debug
    with open(UserDataPath, "wb") as CreateAlarmsSettings:
        pickle.dump(UserData, CreateAlarmsSettings)
    sys.exit()

# GUI: Separately update Tmx file (not used now)
def SepUpdateTmx():
    # Get path to Logical directory
    LogicalPath = GetLogicalPath()

    # Get alarms from global types
    Alarms = GetTypAlarms(LogicalPath)

    # Check properties validity
    Validity()

    # Update Tmx file
    UpdateTmx(LogicalPath, Alarms)

# GUI: Separately update mpalarmxcore file (not used now)
def SepUpdateMpConfig():
    # Get path to Logical directory
    LogicalPath = GetLogicalPath()

    # Get alarms from global types
    Alarms = GetTypAlarms(LogicalPath)

    # Check properties validity
    Validity()

    # Update mpalarmxcore file
    UpdateMpalarmxcore(Alarms)

# GUI: Separately update program file (not used now)
def SepUpdateProgram():
    # Get path to Logical directory
    LogicalPath = GetLogicalPath()

    # Get alarms from global types
    Alarms = GetTypAlarms(LogicalPath)

    # Check properties validity
    Validity()

    # Update program file
    UpdateProgram(LogicalPath, Alarms)

# Prebuild mode function
def Prebuild():
    # Ouput window message
    print("----------------------------- Beginning of the script CreateAlarms -----------------------------")

    # Get path to Logical directory
    LogicalPath = GetLogicalPath()

    # Get alarms from global types
    Alarms = GetTypAlarms(LogicalPath)

    # Check properties validity
    Validity()

    # Update Tmx file
    UpdateTmx(LogicalPath, Alarms)

    # Update mpalarmxcore file
    UpdateMpalarmxcore(Alarms)

    # Update program file
    UpdateProgram(LogicalPath, Alarms)
    
    # Ouput window message
    print("--------------------------------- End of the script CreateAlarms ---------------------------------")

# GUI mode function
def GUI():
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
            color:#ccccdd;
            font: 24px \"Bahnschrift SemiLight SemiConde\";
        }
        
        QLabel{
            background-color:transparent;
            color:#888888;
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

    # Borderless window
    # Dialog.setWindowFlag(Qt.FramelessWindowHint)
    Dialog.setWindowTitle(" ")
    CenterPoint = QDesktopWidget().availableGeometry().center()
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

    # Adding widgets
    ConfigComboBox = QComboBox()
    ConfigComboBox.addItems(ConfigName)
    ConfigComboBox.setToolTip("Select configuration with AlarmsCfg.mpalarmxcore file")
    ConfigComboBox.setCurrentText(UserData["Configuration"])
    ConfigLabel = QLabel("Select configuration")
    ConfigLabel.setToolTip("Select configuration with AlarmsCfg.mpalarmxcore file")
    Layout.addRow(ConfigLabel, ConfigComboBox)

    DebugPushButton = QPushButton("DEBUG")
    DebugPushButton.setToolTip("Turns on printing of debug messages")
    DebugPushButton.setCheckable(True)
    DebugPushButton.setChecked(UserData["Debug"])
    DebugPushButton.setFixedHeight(50)
    DebugLabel = QLabel("Turn on debugging")
    DebugLabel.setToolTip("Turns on printing of debug messages")
    Layout.addRow(DebugLabel, DebugPushButton)

    # RunTmxPushButton = QPushButton("  TMX  ")
    # RunTmxPushButton.setToolTip("Runs TMX update after dialog confirmation")
    # RunTmxPushButton.setFixedHeight(50)
    # RunTmxPushButton.setCheckable(True)
    # RunMpConfigPushButton = QPushButton("  MpAlarmXCore  ")
    # RunMpConfigPushButton.setToolTip("Runs MpAlarmXCore update after dialog confirmation")
    # RunMpConfigPushButton.setFixedHeight(50)
    # RunMpConfigPushButton.setCheckable(True)
    # RunProgramPushButton = QPushButton("  Alarms program  ")
    # RunProgramPushButton.setToolTip("Runs program Alarms update after dialog confirmation")
    # RunProgramPushButton.setFixedHeight(50)
    # RunProgramPushButton.setCheckable(True)
    # RunSeparatelyRow = QHBoxLayout()
    # RunSeparatelyRow.addWidget(RunTmxPushButton)
    # RunSeparatelyRow.addSpacing(10)
    # RunSeparatelyRow.addWidget(RunMpConfigPushButton)
    # RunSeparatelyRow.addSpacing(10)
    # RunSeparatelyRow.addWidget(RunProgramPushButton)
    # UpdateLabel = QLabel("Update after confirmation")
    # UpdateLabel.setToolTip("Updates selected parts after confirmation")
    # Layout.addRow(UpdateLabel, RunSeparatelyRow)
    
    # Creating a dialog button for ok and cancel
    FormButtonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

    # Adding actions for form
    FormButtonBox.accepted.connect(lambda: AcceptConfiguration(ConfigComboBox.currentText(), DebugPushButton.isChecked()))
    FormButtonBox.rejected.connect(Dialog.reject)
    
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

#####################################################################################################################################################
# Main
#####################################################################################################################################################

# Script mode decision
if "-prebuild" in sys.argv:
    # Argument -prebuild found
    RunMode = MODE_PREBUILD
else:
    # Argument -prebuild not found
    RunMode = MODE_GUI

# Get project name
ProjectPath = GetLogicalPath()[:GetLogicalPath().find("Logical") - 1]
ProjectName = os.path.basename(ProjectPath)

# Get path to user data
UserDataPath = os.path.join(os.getenv("APPDATA"), "BR", "CreateAlarms", ProjectName)
if not os.path.isdir(os.path.join(os.getenv("APPDATA"), "BR", "CreateAlarms")):
    os.makedirs(os.path.join(os.getenv("APPDATA"), "BR", "CreateAlarms"))

# Load user data
try:
    with open(UserDataPath, "rb") as CreateAlarmsSettings:
        UserData = pickle.load(CreateAlarmsSettings)
except:
    UserData = {"Configuration":"", "Debug": False}

if (len(UserData) != 2):
    UserData = {"Configuration":"", "Debug": False}

if UserData["Debug"]: print(UserData)

# Run respective script mode
if RunMode == MODE_PREBUILD:
    Prebuild()
elif RunMode == MODE_GUI:
    # TODO GUI:
    # Language selection ?
    GUI()