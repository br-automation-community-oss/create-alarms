import re

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
