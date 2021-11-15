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

__Note: The CreateAlarms script is fully compatible with the AddTask script. When adding an Alarms control task using AddTask, points 4.-6. are met and can be skipped. In addition, adding other task types using AddTask supports rules for the structure and namespace of global data types for this script.__
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
- Each task has its alarms
- Alarms are divided into Error, Warning and Info groups (task does not have to have all of these groups)
- Data type must has gTaskNameAlarmType namespace (i.e. gMotionCtrlErrorType, gMotionCtrlWarningType, gMotionCtrlInfoType)
- Alarms have to be BOOL types
- Properties of alarms must be written into the Description[2] column and separated by semicolon or comma (supported properties see below)
            
## List of supported properties

Properties are key=value pairs in Description[2]. Multiple properties are separated by comma or semicolon.

Values are used to create Alarm List configuration in mpalarmxcore file.

Properties Name and Message are generated automatically.

| Supported properties                      |                                             |
|-------------------------------------------|---------------------------------------------|
| __Key__                                   | __Value__                                   |
| Code                                      | unsigned integer                            |
| Severity                                  | unsigned integer                            |
| Behavior                                  | EdgeAlarm, PersistentAlarm, LevelMonitoring |
| Behavior.MultipleInstances                | FALSE, TRUE                                 |
| Behavior.ReactionUntilAcknowledged        | FALSE, TRUE                                 |
| Behavior.Retain                           | FALSE, TRUE                                 |
| Behavior.Asynchronous                     | FALSE, TRUE                                 |
| Behavior.Monitoring.MonitoredPV           | PV reference                                |
| Behavior.Monitoring.LowLimit              | Disabled, Static, Dynamic                   |
| Behavior.Monitoring.LowLimit.Limit        | float                                       |
| Behavior.Monitoring.LowLimit.LimitPV      | PV reference                                |
| Behavior.Monitoring.LowLimit.LimitText    | string                                      |
| Behavior.Monitoring.HighLimit             | Disabled, Static, Dynamic                   |
| Behavior.Monitoring.HighLimit.Limit       | float                                       |
| Behavior.Monitoring.HighLimit.LimitPV     | PV reference                                |
| Behavior.Monitoring.HighLimit.LimitText   | string                                      |
| Behavior.Monitoring.Settings              | Static, Dynamic                             |
| Behavior.Monitoring.Settings.Delay        | float                                       |
| Behavior.Monitoring.Settings.Hysteresis   | float                                       |
| Behavior.Monitoring.Settings.DelayPV      | PV reference                                |
| Behavior.Monitoring.Settings.HysteresisPV | PV reference                                |
| Disable                                   | FALSE, TRUE                                 |
| AdditionalInformation1                    | string                                      |
| AdditionalInformation2                    | string                                      |

## Version info

__Version 1.2.0:__
- Configuration of sections to update
- Configuration of TMX name
- Configuration of MpConfig name
- Configuration of program name


__Version 1.1.0:__
- Bug with default alarm behavior fixed
- Behavior.Monitoring.MonitoredPV bug fixed
- Tags are taken from the graphics editor
- Monitoring alarm types have no longer Set and Reset in the Alarms program
- Path to user data changed to AppData\Roaming\BR\Scripts\CreateAlarms\
- Error mode added
	
__Version 1.0.0:__

- Script creation
- Basic functions implemented
