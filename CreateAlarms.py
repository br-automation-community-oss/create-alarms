#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os
import re
import sys

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
    Valid = False
    Value = ""
    
    def __init__(self, Name, Key, Task, Valid, Value):
        self.Name = Name
        self.Key = Key
        self.Task = Task
        self.Valid = Valid
        self.Value = Value

    def __str__(self) -> str:
        return("["+self.Name+","+str(self.Key)+","+self.Task+","+str(self.Valid)+","+self.Value+"]")

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
PatternStructure = r"g([a-zA-Z0-9]{1,10})(Error|Info|Warning)Type[^\n]+\n([\s\S]*?)END_STRUCT"
PatternMember = r"([a-zA-Z0-9_]{1,32}).*?BOOL\s?\(\*.*?\*\)\s?\(\*(.*?)\*\).?\n"
PatternPair = r"([a-zA-Z0-9]*)[ ]{0,}=[ ]{0,}([a-zA-Z0-9]*)"

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
                Properties.append(PropertyClass(Member[0], Index, Structure[0], True, Pair[1]))
            except ValueError:
                print("[Warning] Key '"+Key+"' of member '"+Structure[0]+Structure[1]+"."+Member[0]+"' is not valid.")

#####################################################################################################################################################
# Debug print
#####################################################################################################################################################
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
if os.path.isfile(TmxPath):
    TmxFile = open(TmxPath, "r")
    
    # Get alarm names

    TmxFile.close()
else:
    print("File Global.typ does not exist.")
    sys.exit()