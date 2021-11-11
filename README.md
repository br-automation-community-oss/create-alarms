# CreateAlarms

Creates alarm handling from global type definitions.

## Description

The script reads alarms from Global.typ file and generates tmx texts, Set/Reset functions and MpAlarmXCore alarm list.

The script is run in the prebuild part with the -prebuild argument, when it is double-clicked in AS, the GUI of its configuration is shown.

How does the script work?

    1. Alarms from global types are read (these must have a defined structure of gTaskNameAlarmType data type names)
    2. The detected alarms are written to a tmx file (there you then have to write the texts by yourself)
    3. In the Alarms program are generated Set/Reset functions in the section marked for automatic generation
    4. In the selected configuration, alarms in AlarmsCfg.mpalarmxcore are generated

## Implementation to your project

    1. Add the CreateAlarms.py script to the LogicalView in your project (can also be in subfolders)
    2. Add script to prebuild events with "-prebuild" argument
        $(AS_PROJECT_PATH)/Logical/Scripts/CreateAlarms.py -prebuild
    3. Run script by double-click in AS and setup script configuration, then press OK
    4. Task Alarms with Alarms.c (or Alarms.st), Alarms.typ, Alarms.var and Alarms.tmx must be Inserted to LogicalView
        (can be also in subfolders)
    5. In Alarms.c (or Alarms.st) and Alarms.typ must be defined section for automatic code generation
        // START OF AUTOMATIC CODE GENERATION //
        // END OF AUTOMATIC CODE GENERATION //
    6. Alarms.tmx must has namespace "Alarms"
    7. In the configuration selected in the script configuration, there must be AlarmsCfg.mpalarmxcore file
    8. Alarms in Global.typ have to meet this requirements
        a) Each task has its alarms
        b) Alarms are divided into Error, Warning and Info groups (task does not have to have all of these groups)
        c) Data type must has gTaskNameAlarmType namespace
            (i.e. gMotionCtrlErrorType, gMotionCtrlWarningType, gMotionCtrlInfoType)
        d) Alarms have to be BOOL types
        e) Properties of alarms must be written into the Description[2] column and separated by semicolon or comma
            (supported properties see below)
            
## List of supported properties

Properties are key=value pairs in Description[2]. Multiple properties are separated by comma or semicolon.

Values are used to create Alarm List configuration in mpalarmxcore file.

Properties Name and Message are generated automatically.

| Supported properties               |                            |
|------------------------------------|----------------------------|
| __Key__                            | __Value__                  |
| Code                               | unsigned integer           |
| Severity                           | unsigned integer           |
| Behavior                           | EdgeAlarm, PersistentAlarm |
| Behavior.Retain                    | FALSE, TRUE                |
| Behavior.Async                     | FALSE, TRUE                |
| Behavior.MultipleInstances         | FALSE, TRUE                |
| Behavior.ReactionUntilAcknowledged | FALSE, TRUE                |
| Disable                            | FALSE, TRUE                |
| AdditionalInformation1             | string                     |
| AdditionalInformation2             | string                     |

## Version info

Version 1.0.0:

- Script creation
- Basic functions implemented
