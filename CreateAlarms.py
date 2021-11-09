#   Copyright:  B&R Industrial Automation
#   Authors:    Adam Sefranek, Michal Vavrik
#   Created:	Oct 26, 2021 1:36 PM
#   Version:	1.0.0

#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os, sys
import xml.etree.ElementTree as et
from GetAlarms import GetAlarms, CreateTreeFromProperties
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
import pickle

#####################################################################################################################################################
# Debug mode (debug print)
#####################################################################################################################################################
DEBUG = False

#####################################################################################################################################################
# Global constants
#####################################################################################################################################################
MODE_PREBUILD = 0
MODE_GUI = 1
LANGUAGE_C = 0
LANGUAGE_ST = 1
EXTENSIONS = [".c", ".st"]

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
        sys.exit("Error: File " + FileName + " does not exist.")
    return FilePath

# Checks if file exists and terminates script if not
def IsFile(FilePath):
    if not os.path.isfile(FilePath):
        sys.exit("Error: File " + os.path.basename(FilePath) + " does not exist.")
    return True

# Checks if directory exists and terminates script if not
def IsDir(DirPath):
    if not os.path.isdir(DirPath):
        sys.exit("Error: Directory " + DirPath + " does not exist.")
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
        sys.exit("Error: Directory 'Logical' does not exist.")
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

# Update mpalarmxcore file
def UpdateMpalarmxcore(Alarms):
    #####################################################################################################################################################
    # Update mpalarmxcore
    #####################################################################################################################################################

    # Ouput window message
    print("Updating AlarmsCfg.mpalarmxcore file...")

    # Create path to mpalarmxcore
    ConfigName = []
    ConfigPath = os.path.dirname(os.path.abspath(__file__))
    ConfigPath = ConfigPath[:ConfigPath.find("Logical")]
    MpAlarmPath = FindFilePath(ConfigPath, "AlarmsCfg.mpalarmxcore", True)

    # CpuPath = os.path.join(ConfigPath, ConfigName[0])
    # for Cpu in os.listdir(CpuPath):
    #     TmpPath = os.path.join(CpuPath, Cpu)
    #     if os.path.isdir(os.path.join(CpuPath, Cpu)):
    #         CpuPath = os.path.join(CpuPath, Cpu)

    # MpAlarmPath = os.path.join(CpuPath, "mappServices", "AlarmsCfg.mpalarmxcore")

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
        sys.exit("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
    elif InAutomaticSection:
        sys.exit("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
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
        sys.exit("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
    elif InAutomaticSection:
        sys.exit("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
    else:
        AlarmsTypFile = open(AlarmsTypPath,"w")
        AlarmsTypFile.write(AlarmsTypText)
        AlarmsTypFile.close()

# GUI configuration accepted
def AcceptConfiguration(Config):
    UserData["Configuration"] = Config
    with open(os.getenv("APPDATA") + "\\BR\\" + "CreateAlarmsSettings", "wb") as CreateAlarmsSettings:
        pickle.dump(UserData, CreateAlarmsSettings)
    sys.exit()

# Separately update Tmx file
def SepUpdateTmx():
    # Get path to Logical directory
    LogicalPath = GetLogicalPath()

    # Get alarms from global types
    Alarms = GetTypAlarms(LogicalPath)

    # Check properties validity
    Validity()

    # Update Tmx file
    UpdateTmx(LogicalPath, Alarms)

# Separately update mpalarmxcore file
def SepUpdateMpConfig():
    # Get path to Logical directory
    LogicalPath = GetLogicalPath()

    # Get alarms from global types
    Alarms = GetTypAlarms(LogicalPath)

    # Check properties validity
    Validity()

    # Update mpalarmxcore file
    UpdateMpalarmxcore(Alarms)

# Separately update program file
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
            background-color:#222222;
            color:#ccccdd;
            font: 24px \"Bahnschrift SemiLight SemiConde\";
        }

        QLineEdit{
            background-color:#111111;
            color:#ccccdd;
            border:6;
            padding-left:10px;
        }

        QComboBox{
            background-color:#111111;
            color:#ccccdd;
            border:6;
            padding: 10px;
        }

        QCheckBox{
            border-style:none;
        }

        QCheckBox::indicator{
            top:2px;
            width:30px;
            height:30px;
            background-color:#111111;
            color:#ff0000;
        }

        QCheckBox::indicator:hover{
            background-color:#333333;
        }

        QCheckBox::indicator:checked{
            background-color:limegreen;
        }

        QCheckBox::indicator:disabled{
            background-color:#303030;
        }

        QRadioButton{
            border-style:none;
        }

        QRadioButton::indicator{
            top:2px;
            width:24px;
            height:24px;
            border-radius:12px;
            background-color:#111111;
            color:#ff0000;
        }

        QRadioButton::indicator:hover{
            background-color:#333333;
        }

        QRadioButton::indicator:checked{
            background-color:limegreen;
        }

        QRadioButton::indicator:disabled{
            background-color:#303030;
        }

        QDialogButtonBox::StandardButton *{
            background-color:#333333;
            width:120px;
        }

        QPushButton{
            background-color:#111111;
            border: none;
            padding: 10px;
        }

        QPushButton:pressed{
            background-color:limegreen;
            color:#111111;
            border: none;
        }

        QPushButton:checked{
            background-color:limegreen;
            color:#111111;
            border: none;
        }

        QToolTip{
            font: 16px \"Bahnschrift SemiLight SemiConde\";
            background-color:#eedd22;
            color:#111111;
            border: solid black 1px;
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
    ConfigComboBox = QComboBox(parent=FormGroupBox)
    ConfigComboBox.addItems(ConfigName)
    ConfigComboBox.setToolTip("Select configuration with AlarmsCfg.mpalarmxcore file")
    ConfigLabel = QLabel("Select configuration")
    ConfigLabel.setToolTip("Select configuration with AlarmsCfg.mpalarmxcore file")
    Layout.addRow(ConfigLabel, ConfigComboBox)

    RunTmxPushButton = QPushButton("Update TMX")
    RunTmxPushButton.setToolTip("Immidiately runs TMX update")
    RunMpConfigPushButton = QPushButton("Update MpAlarmXCore")
    RunMpConfigPushButton.setToolTip("Immidiately runs MpAlarmXCore update")
    RunProgramPushButton = QPushButton("Update program")
    RunProgramPushButton.setToolTip("Immidiately runs program Alarms update")
    RunSeparatelyRow = QHBoxLayout()
    RunSeparatelyRow.addSpacing(10)
    RunSeparatelyRow.addWidget(RunTmxPushButton)
    RunSeparatelyRow.addSpacing(20)
    RunSeparatelyRow.addWidget(RunMpConfigPushButton)
    RunSeparatelyRow.addSpacing(20)
    RunSeparatelyRow.addWidget(RunProgramPushButton)
    RunSeparatelyRow.addSpacing(10)
    RunSeparatelyRow.addSpacerItem(QSpacerItem(0, 80))
    Layout.addRow(RunSeparatelyRow)

    RunScriptPushButton = QPushButton("Update all")
    RunScriptPushButton.setToolTip("Immidiately runs the script")
    RunScriptRow = QHBoxLayout()
    RunScriptRow.addSpacing(120)
    RunScriptRow.addWidget(RunScriptPushButton)
    RunScriptRow.addSpacing(120)
    RunScriptRow.addSpacerItem(QSpacerItem(0, 40))
    Layout.addRow(RunScriptRow)

    # Creating a dialog button for ok and cancel
    FormButtonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

    # Adding actions for form
    FormButtonBox.accepted.connect(lambda: AcceptConfiguration(ConfigComboBox.currentText()))
    FormButtonBox.rejected.connect(Dialog.reject)
    RunTmxPushButton.clicked.connect(SepUpdateTmx)
    RunMpConfigPushButton.clicked.connect(SepUpdateMpConfig)
    RunProgramPushButton.clicked.connect(SepUpdateProgram)
    RunScriptPushButton.clicked.connect(Prebuild)
    
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

# Load user settings
try:
    with open(os.getenv("APPDATA") + "\\BR\\" + "CreateAlarmsSettings", "rb") as CreateAlarmsSettings:
        UserData = pickle.load(CreateAlarmsSettings)
except:
    UserData = {"Configuration":""}

# Run respective script mode
if RunMode == MODE_PREBUILD:
    Prebuild()
elif RunMode == MODE_GUI:
    # TODO GUI:
    # Language selection ?
    # Configuration selection for more projects {"Project":{"Name":"", "Configuration":""}}
    # DEBUG buttons
    GUI()