#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os
import re
import sys
import xml.etree.ElementTree as et

#####################################################################################################################################################
# Debug mode (debug print)
#####################################################################################################################################################
DEBUG = True

#####################################################################################################################################################
# List of possible properties
#####################################################################################################################################################
KEYS = ["Code", "Severity", "Behavior"]

#####################################################################################################################################################
# Class definition
#####################################################################################################################################################
class PropertyClass:
    Name = ""
    Key = 0        # Index to KEYS list
    Task = ""
    Type = ""
    Valid = False
    Value = ""
    
    def __init__(self, Name, Key, Task, Type, Valid, Value):
        self.Name = Name
        self.Key = Key
        self.Task = Task
        self.Type = Type
        self.Valid = Valid
        self.Value = Value

    def __str__(self) -> str:
        return("["+self.Task+","+self.Type+","+self.Name+","+str(self.Key)+","+self.Value+","+str(self.Valid)+"]")

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

Properties = []
Structures = re.findall(PatternStructure, TypContent)
for Structure in Structures:
    Members = re.findall(PatternMember, Structure[2])
    for Member in Members:
        Pairs = re.findall(PatternPair, Member[1])
        for Pair in Pairs:
            try:
                Key = Pair[0].capitalize()
                Index = KEYS.index(Key)
                Properties.append(PropertyClass(Member[0], Index, Structure[0], Structure[1], True, Pair[1]))
            except ValueError:
                print("Warning: Key '"+Key+"' of member 'g"+Structure[0]+Structure[1]+"Type."+Member[0]+"' is not valid.")

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

if DEBUG:
    print("Tmx alamrs: " + str(TmxAlarms))

#####################################################################################################################################################
# Get alarm names from Global.typ with unique alarm name
#####################################################################################################################################################
# Get all alarm names
TypAlarms = []
for Item in Properties:
    TypAlarms.append("g" + Item.Task + "." + Item.Type + "." + Item.Name)
# Convert list to set to get unique names
TypAlarms = set(TypAlarms)

if DEBUG:
    print("Typ alarms: " + str(TypAlarms))

#####################################################################################################################################################
# Compare alarm names
#####################################################################################################################################################
NewAlarms = list(set(TypAlarms) - set(TmxAlarms))
MissingAlarms = list(set(TmxAlarms) - set(TypAlarms))
if DEBUG:
    print("New alamrs are: " + str(NewAlarms))
    print("Missing alamrs are: " + str(MissingAlarms))

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
    if (TmxLine.find("</body>") != -1): # End found
        for NewAlarm in NewAlarms:
            TmxText += "\t<tu tuid=\"" + NewAlarm + "\" />\n"
    TmxText += TmxLine
TmxFile.close()
TmxFile = open(TmxPath,"w")
TmxFile.write(TmxText)
TmxFile.close()

#TmxTree = et.parse(TmxPath)
#TmxRoot = TmxTree.getroot()
#TmxBody = TmxRoot.find("//body")
#print(TmxBody)


# try:
#     Index = TmxAlarms.index(Item.Name)
#     print("Info: Alarm '"+Item.Name+"' already exists in Alarms.tmx file.")
# except ValueError:
#     print("Create '"+Item.Name+"' in Alarms.tmx file.")
