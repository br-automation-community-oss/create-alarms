# CreateAlarms

Creates alarm handling from global type definitions.

## Description

The script reads alarms from Global.typ file and generates tmx texts, Set/Reset functions and MpAlarmXCore alarm list.

The script is run in the prebuild part with the -prebuild argument, when it is double-clicked in AS, the GUI of its configuration is shown.

How does the script work?

1. Alarms from global variables a read
2. All possible paths to alarm structures are determined
3. The detected alarms are written to a tmx file (there you then have to write the texts by yourself)
4. In the Alarms program are generated Set/Reset functions in the section marked for automatic generation
5. In the selected configuration, alarms in AlarmsCfg.mpalarmxcore are generated

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
- Alarms are divided into Error, Warning and Info groups (each data type containing the word "Error", "Warning" or "Info" is taken as an alarm data type and is taken into account when generating the code)
- Alarms have to be BOOL types
- Properties of alarms must be written into the Description[2] column and separated by semicolon or comma (supported properties see below)

## List of supported properties

Properties are key=value pairs in Description[2]. Multiple properties are separated by comma or semicolon.

Values are used to create Alarm List configuration in mpalarmxcore file.

Properties Name and Message are generated automatically.

| Supported properties                      			|                                             |
|-------------------------------------------------------|---------------------------------------------|
| __Key__												| __Value__                                   |
| Code													| unsigned integer                            |
| Severity                               			   	| unsigned integer                            |
| Behavior                               			   	| EdgeAlarm, PersistentAlarm                  |
| Behavior.MultipleInstances             			   	| FALSE, TRUE                                 |
| Behavior.ReactionUntilAcknowledged	        		| FALSE, TRUE                                 |
| Behavior.Retain										| FALSE, TRUE                                 |
| Behavior.Asynchronous                     			| FALSE, TRUE                                 |
| Behavior.DataUpdate.Activation.Timestamp  			| FALSE, TRUE                                 |
| Behavior.DataUpdate.Activation.Snippets   			| FALSE, TRUE                                 |
| Behavior.HistoryReport.InactiveToActive   			| FALSE, TRUE                                 |
| Behavior.HistoryReport.ActiveToInactive   			| FALSE, TRUE                                 |
| Behavior.HistoryReport.UnacknowledgedToAcknowledged   | FALSE, TRUE                                 |
| Behavior.HistoryReport.AcknowledgedToUnacknowledged   | FALSE, TRUE                                 |
| Behavior.HistoryReport.Update							| FALSE, TRUE                                 |
| Disable												| FALSE, TRUE                                 |
| AdditionalInformation1								| string                                      |
| AdditionalInformation2								| string                                      |

## Version info
__Version 2.0.1__
- Once nested alarms path bug fixed
- Supported properties change
- Print of used configuration
- Invalid property name bug fixed
	
__Version 2.0.0__
- New system of finding alarm paths
- Support of arrays (also defined by constants)

__Version 1.2.0__
- Configuration of sections to update
- Configuration of TMX, MpConfig and program name
- Properties validity
- Strings must be in quotation marks

__Version 1.1.0__
- Bug with default alarm behavior fixed
- Behavior.Monitoring.MonitoredPV bug fixed
- Tags are taken from the graphics editor
- Monitoring alarm types have no longer Set and Reset in the Alarms program
- Path to user data changed to AppData\Roaming\BR\Scripts\CreateAlarms\
- Error mode added
	
__Version 1.0.0__

- Script creation
- Basic functions implemented
