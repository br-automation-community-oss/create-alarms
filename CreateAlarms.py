#   Copyright:  B&R Industrial Automation
#   Authors:    Adam Sefranek, Michal Vavrik
#   Created:	Oct 26, 2021 1:36 PM

# TODO
# Lépe organizovat SetReset alarmů v poli: společné FORy, kde to jde + Flagy pro struktury

#####################################################################################################################################################
# Dependencies
#####################################################################################################################################################
import os, re, sys
import xml.etree.ElementTree as et
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pickle

#####################################################################################################################################################
# Global constants and variables
#####################################################################################################################################################
# General
WINDOW_TITLE = "GUI Template"
SCRIPT_VERSION = "2.1.0"

# Window style
WINDOW_COLOR_STYLE = "#4a2c0d"
DEFAULT_GUI_SIZE = {"TitleFontSize": 30, "FontSize": 24, "TooltipFontSize": 16, "WidgetHeight": 50, "ButtonWidth": 180}
gSizeRatio = 1
gAdjustedGuiSize = {}

MODE_PREBUILD = 0
MODE_CONFIGURATION = 1
MODE_ERROR = 2
LANGUAGE_C = 0
LANGUAGE_ST = 1
EXTENSIONS = [".c", ".st"]
PERMITTED_TYPES_OF_ARRAY_CONSTANTS = ["USINT", "SINT", "UINT", "INT", "UDINT", "DINT"]

# Validity ranges
RANGE_UDINT = [0, 4294967295]
RANGE_REAL = [-3.4E38, 3.4E38]
RANGE_LREAL = [-1.797E308, 1.797E308]
RANGE_BOOL = ["FALSE", "TRUE", "False", "True", "false", "true"]
RANGE_BEHAVIOR = ["EdgeAlarm", "PersistentAlarm", "UserDefined"]
RANGE_DIS_STAT_DYN = ["Disabled", "Static", "Dynamic"]
RANGE_STAT_DYN = ["Static", "Dynamic"]
RANGE_ACKNOWLEDGE = [0, 3]
RANGE_NONE = [None]

# Each key represents allowed alarm property, its value is XML element tag
PROPERTIES = {"Code": {"Tag": "Property", "ID": "Code", "Validity": RANGE_UDINT},
			  "Severity": {"Tag": "Property", "ID": "Severity", "Validity": RANGE_UDINT},
			  "Behavior": {"Tag": "Selector", "ID": "Behavior", "Validity": RANGE_BEHAVIOR},
			  "Behavior.AutoReset": {"Tag": "Property", "ID": "AutoReset", "Validity": RANGE_BOOL},
			  "Behavior.Acknowledge": {"Tag": "Property", "ID": "Acknowledge", "Validity": RANGE_ACKNOWLEDGE},
			  "Behavior.MultipleInstances": {"Tag": "Property", "ID": "MultipleInstances", "Validity": RANGE_BOOL},
			  "Behavior.ReactionUntilAcknowledged": {"Tag": "Property", "ID": "ReactionUntilAcknowledged", "Validity": RANGE_BOOL},
			  "Behavior.Retain": {"Tag": "Property", "ID": "Retain", "Validity": RANGE_BOOL},
			  "Behavior.Asynchronous": {"Tag": "Property", "ID": "Async", "Validity": RANGE_BOOL},
			  "Behavior.DataUpdate": {"Tag": "Group", "ID": "DataUpdate", "Validity": RANGE_NONE},
			  "Behavior.DataUpdate.Activation": {"Tag": "Group", "ID": "Activation", "Validity": RANGE_NONE},
			  "Behavior.DataUpdate.Activation.Timestamp": {"Tag": "Property", "ID": "TimeStamp", "Validity": RANGE_BOOL},
			  "Behavior.DataUpdate.Activation.Snippets": {"Tag": "Property", "ID": "Snippets", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport": {"Tag": "Group", "ID": "Recording", "Validity": RANGE_NONE},
			  "Behavior.HistoryReport.InactiveToActive": {"Tag": "Property", "ID": "InactiveToActive", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.ActiveToInactive": {"Tag": "Property", "ID": "ActiveToInactive", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.UnacknowledgedToAcknowledged": {"Tag": "Property", "ID": "UnacknowledgedToAcknowledged", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.AcknowledgedToUnacknowledged": {"Tag": "Property", "ID": "AcknowledgedToUnacknowledged", "Validity": RANGE_BOOL},
			  "Behavior.HistoryReport.Update": {"Tag": "Property", "ID": "Update", "Validity": RANGE_BOOL},
			  "Disable": {"Tag": "Property", "ID": "Disable", "Validity": RANGE_BOOL},
			  "AdditionalInformation1": {"Tag": "Property", "ID": "AdditionalInformation1", "Validity": RANGE_NONE},
			  "AdditionalInformation2": {"Tag": "Property", "ID": "AdditionalInformation2", "Validity": RANGE_NONE}}

# Patterns for global types parsing
	# Matches structure definition, returns 2 groups:
	# 1. Name of the structure
	# 2. Members of the structure
PATTERN_STRUCTURE = r"([a-zA-Z0-9_]{1,32})\s{0,}:\s{0,}STRUCT[^\n]{0,}\n([\s\S]*?)\s{0,}END_STRUCT"

	# Matches type members structure definition, returns 10 groups:
	# 1. Name of array variables
	# 2. Start value of array
	# 3. End value of array
	# 4. Type of array variables
	# 5. Descriptions 1 and 2 of array variables
	# 6. Description 2 of array variables
	# 7. Name of non array variables
	# 8. Type of non array variables
	# 9. Descriptions 1 and 2 of non array variables
	# 10. Description 2 of non array variables
PATTERN_MEMBER = r"([a-zA-Z0-9_]{1,32}).*?ARRAY\[([a-zA-Z0-9_-]+)..([a-zA-Z0-9_-]+)\]\s{0,}OF\s{0,}([a-zA-Z0-9_]+)\s{0,};\s{0,}(\(\*.*?\*\)\s*?\(\*(.+?)\*\)\s*?)?\n{0,1}|([a-zA-Z0-9_]{1,32}).*?([a-zA-Z0-9_]{1,32})\s{0,};\s{0,}(\(\*.*?\*\)\s*?\(\*(.+?)\*\)\s*?)?\n{0,1}"

	# Matches Key=Value pairs, returns 2 groups:
	# 1. Key
	# 2. Value
PATTERN_PAIR = r"([a-zA-Z0-9.]+)[ ]*?=[ ]*?([a-zA-Z0-9.:-]+|\"[^;]+\")"

# Patterns for global variables and constants parsing
	# Matches VAR sections, returns 3 groups:
	# 1. VAR RETAIN section
	# 2. VAR CONSTANT section
	# 3. VAR section
PATTERN_VAR_SECTION = r"VAR RETAIN\s{0,}\n\s{0,}([\s\S]*?)\n\s{0,}END_VAR|VAR CONSTANT\s{0,}\n\s{0,}([\s\S]*?)\n\s{0,}END_VAR|VAR[^\na-zA-Z]{0,}\n\s{0,}([\s\S]*?)\n\s{0,}END_VAR"

	# Matches variables in sections, returns 7 groups:
	# 1. Variable name of non array variables
	# 2. UNREPLICABLE tag
	# 3. Type of non array variables
	# 4. Variable name of array variables
	# 5. Start value of array
	# 6. End value of array
	# 7. Type of array variables
PATTERN_VARIABLE = r"([a-zA-Z0-9_]+)\s{0,}:\s{0,}(\{REDUND_UNREPLICABLE\}){0,1}\s{0,}([a-zA-Z0-9_]+)[^;\[\]]{0,};|([a-zA-Z0-9_]+)\s{0,}:\s{0,}ARRAY\[([a-zA-Z0-9_-]+)..([a-zA-Z0-9_-]+)\]\s{0,}OF\s{0,}([a-zA-Z0-9_]+)[^;]{0,};"

	# Matches constants in sections, returns 3 groups:
	# 1. Name
	# 2. Type
	# 3. Value
PATTERN_CONSTANT = r"([a-zA-Z0-9_]+)\s{0,}:\s{0,}([a-zA-Z0-9_]+)\s{0,}:=\s{0,}([^;]+);"

	# Matches inner constants in constants value, returns 1 group:
	# 1. Inner constant name
PATTERN_CONSTANT_VALUE = r"([a-zA-Z][a-zA-Z0-9_]{0,})"

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

	def append(self, obj) -> object:
		self.children.append(obj)
		return obj

	def find(self, key):
		return next(iter([node for node in self.children if node.key == key]), None)

# Main GUI window
class MainWindow(QWidget):
	# Initialization of the window
	def __init__(Self):
		super(MainWindow, Self).__init__()

		# Window functions
		Self.CreateGlobalWidgets()
		Self.CreateFormWidgets()
		Self.CreateActions()

		# Show window
		ShowAdjusted(Self)

	# Global widgets of the window
	def CreateGlobalWidgets(Self):
		# Set frameless window
		Self.setWindowFlags(Self.windowFlags() | Qt.FramelessWindowHint)
		Self.setWindowTitle(WINDOW_TITLE)

		# Create title bar
		Self.TitleBar = TitleBar(Self, WINDOW_TITLE, WINDOW_COLOR_STYLE, True, True, True)
		Self.setContentsMargins(0, Self.TitleBar.height(), 0, 0)

		# Create bottom button bar
		Self.BottomBar = BottomBar(Self)
		
		# Create info dialog to inform the user
		Self.InfoD = InfoDialog()

		# Adjust window size
		Self.resize(800, Self.TitleBar.height())
		Self.setMaximumSize(1920, 1080)

		# Set window styles
		Style = """
		QWidget {
			background-color: qlineargradient(spread:pad, x1:1, y1:0, x2:1, y2:1, stop:0 #000000, stop:1 #141414);
			color: #cccccc;
			font: ReplaceFontSizepx \"Bahnschrift SemiLight SemiConde\";
		}

		QGroupBox {
			border: 2px solid;
			border-color: ReplaceColor;
		}

		QToolTip {
			background-color: #eedd22;
			color: #111111;
			font: ReplaceTooltipFontSizepx \"Bahnschrift SemiLight SemiConde\";
			border: solid black 1px;
		}

		QLabel {
			background-color: transparent;
			color: #888888;
		}

		QLineEdit {
			background-color: #3d3d3d;
			color: #cccccc;
			border-radius: 8px;
			padding-left: 10px;
			height: ReplaceWidgetHeightpx;
		}

		QLineEdit:hover {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #373737, stop:0.505682 #373737, stop:1 #282828);
			color: #cccccc;
		}

		QPushButton {
			background-color: #3d3d3d;
			color: #cccccc;
			width: ReplaceButtonWidthpx;
			height: ReplaceWidgetHeightpx;
			border-style: solid;
			border-radius: 8px;
		}

		QPushButton:hover {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #373737, stop:0.505682 #373737, stop:1 #282828);
			color: #cccccc;
		}

		QPushButton:pressed {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #2d2d2d, stop:0.505682 #282828, stop:1 #2d2d2d);
			color: #ffffff;
		}
		
		QPushButton:checked {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #095209, stop:1 #0e780e);
			color:#ffffff;
		}

		QPushButton:checked:hover {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #084209, stop:1 #0c660e);
		}

		QPushButton:checked:pressed {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #083108, stop:1 #0d570d);
		}

		QCheckBox {
			background-color: transparent;
			border-style: none;
		}

		QCheckBox::indicator {
			background-color: #3d3d3d;
			top: 2px;
			width: ReplaceWidgetHeightpx;
			height: ReplaceWidgetHeightpx;
			border-radius: 8px;
			margin-bottom: 4px;
		}

		QCheckBox::indicator:hover {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #373737, stop:0.505682 #373737, stop:1 #282828);
		}

		QCheckBox::indicator:pressed {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #2d2d2d, stop:0.505682 #282828, stop:1 #2d2d2d);
		}
		
		QCheckBox::indicator:checked {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #095209, stop:1 #0e780e);
		}

		QCheckBox::indicator:checked:hover {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #084209, stop:1 #0c660e);
		}

		QCheckBox::indicator:checked:pressed {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #083108, stop:1 #0d570d);
		}

		QComboBox {
			background-color: #3d3d3d;
			color: #cccccc;
			height: ReplaceWidgetHeightpx;
			border: none;
			border-radius: 8px;
			padding-left: 10px;
		}

		QComboBox:hover {
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #373737, stop:0.505682 #373737, stop:1 #282828);
			color: #cccccc;
		}
		
		QComboBox::drop-down {
			background-color: #282828;
			width: 20px;
			border-top-right-radius: 8px;
			border-bottom-right-radius: 8px;
		}

		QComboBox QAbstractItemView {
			background-color: #3d3d3d;
			color: #cccccc;
		}
		"""
		Self.setStyleSheet(FinishStyle(Style))

		# Create main group box
		Self.MainGB = QGroupBox(Self)
		Self.MainGB.setGeometry(0, Self.TitleBar.height(), Self.width(), Self.height() - Self.TitleBar.height())

		# Create a form Layout
		Self.LayoutFL = QFormLayout()
		Self.LayoutFL.setHorizontalSpacing(20)

		# Set layout of window
		MainVBL = QVBoxLayout(Self)
		MainVBL.addLayout(Self.LayoutFL)
		MainVBL.addWidget(Self.BottomBar.BottomBarGB)

	# Form widgets
	def CreateFormWidgets(Self):
		# Configuration selection
		Self.ConfigComboBox = QComboBox()
		Self.ConfigComboBox.addItems(ConfigName)
		Self.ConfigComboBox.setToolTip("Select configuration with .mpalarmxcore file")
		Self.ConfigComboBox.setCurrentText(UserData["Configuration"])
		ConfigLabel = QLabel("Select configuration")
		ConfigLabel.setToolTip("Select configuration with .mpalarmxcore file")
		Self.LayoutFL.addRow(ConfigLabel, Self.ConfigComboBox)

		# Debug option
		Self.DebugPushButton = QPushButton("DEBUG")
		Self.DebugPushButton.setToolTip("Turns on printing of debug messages")
		Self.DebugPushButton.setCheckable(True)
		Self.DebugPushButton.setChecked(UserData["Debug"])
		Self.DebugPushButton.setFixedHeight(50)
		DebugLabel = QLabel("Turn on debugging")
		DebugLabel.setToolTip("Turns on printing of debug messages")
		Self.LayoutFL.addRow(DebugLabel, Self.DebugPushButton)

		# Tmx name
		Self.TmxNameLineEdit = QLineEdit()
		Self.TmxNameLineEdit.setToolTip("Name of the tmx file without .tmx extension")
		Self.TmxNameLineEdit.setText(UserData["TmxName"])
		Self.TmxNameLineEdit.setFixedHeight(50)
		TmxNameLabel = QLabel("Tmx name")
		TmxNameLabel.setToolTip("Name of the tmx file without .tmx extension")
		TmxExtensionLabel = QLabel(".tmx")
		TmxExtensionLabel.setToolTip("Name of the tmx file without .tmx extension")
		Self.TmxNameRow = QHBoxLayout()
		Self.TmxNameRow.addWidget(Self.TmxNameLineEdit)
		Self.TmxNameRow.addSpacing(10)
		Self.TmxNameRow.addWidget(TmxExtensionLabel)
		Self.LayoutFL.addRow(TmxNameLabel, Self.TmxNameRow)

		# MpConfig name
		Self.MpConfigNameLineEdit = QLineEdit()
		Self.MpConfigNameLineEdit.setToolTip("Name of the MpConfig file without .mpalarmxcore extension (cannot be same as program name)")
		Self.MpConfigNameLineEdit.setText(UserData["MpConfigName"])
		Self.MpConfigNameLineEdit.setFixedHeight(50)
		MpConfigNameLabel = QLabel("MpConfig name")
		MpConfigNameLabel.setToolTip("Name of the MpConfig file without .mpalarmxcore extension (cannot be same as program name)")
		MpConfigExtensionLabel = QLabel(".mpalarmxcore")
		MpConfigExtensionLabel.setToolTip("Name of the MpConfig file without .mpalarmxcore extension (cannot be same as program name)")
		Self.MpConfigNameRow = QHBoxLayout()
		Self.MpConfigNameRow.addWidget(Self.MpConfigNameLineEdit)
		Self.MpConfigNameRow.addSpacing(10)
		Self.MpConfigNameRow.addWidget(MpConfigExtensionLabel)
		Self.LayoutFL.addRow(MpConfigNameLabel, Self.MpConfigNameRow)

		# Program name
		Self.ProgramNameLineEdit = QLineEdit()
		Self.ProgramNameLineEdit.setToolTip("Name of the program file without .st/.c extension (cannot be same as MpConfig name)")
		Self.ProgramNameLineEdit.setText(UserData["ProgramName"])
		Self.ProgramNameLineEdit.setFixedHeight(50)
		ProgramNameLabel = QLabel("Program name")
		ProgramNameLabel.setToolTip("Name of the program file without .st/.c extension (cannot be same as MpConfig name)")
		ProgramExtensionLabel = QLabel(".st/.c")
		ProgramExtensionLabel.setToolTip("Name of the program file without .st/.c extension (cannot be same as MpConfig name)")
		Self.ProgramNameRow = QHBoxLayout()
		Self.ProgramNameRow.addWidget(Self.ProgramNameLineEdit)
		Self.ProgramNameRow.addSpacing(10)
		Self.ProgramNameRow.addWidget(ProgramExtensionLabel)
		Self.LayoutFL.addRow(ProgramNameLabel, Self.ProgramNameRow)

		# Sections update
		Self.UpdateTmxCheckBox = QCheckBox("Update TMX")
		Self.UpdateTmxCheckBox.setToolTip("The script will update the TMX file every build")
		Self.UpdateTmxCheckBox.setFixedHeight(50)
		Self.UpdateTmxCheckBox.setChecked(UserData["UpdateTmx"])
		Self.UpdateMpConfigCheckBox = QCheckBox("Update MpConfig")
		Self.UpdateMpConfigCheckBox.setToolTip("The script will update the MpAlarmXCore file every build")
		Self.UpdateMpConfigCheckBox.setFixedHeight(50)
		Self.UpdateMpConfigCheckBox.setChecked(UserData["UpdateMpConfig"])
		Self.UpdateProgramCheckBox = QCheckBox("Update Set/Reset")
		Self.UpdateProgramCheckBox.setToolTip("The script will update the .st/.c program file every build")
		Self.UpdateProgramCheckBox.setFixedHeight(50)
		Self.UpdateProgramCheckBox.setChecked(UserData["UpdateProgram"])
		Self.UpdateSectionRow = QHBoxLayout()
		Self.UpdateSectionRow.addWidget(Self.UpdateTmxCheckBox)
		Self.UpdateSectionRow.addSpacing(10)
		Self.UpdateSectionRow.addWidget(Self.UpdateMpConfigCheckBox)
		Self.UpdateSectionRow.addSpacing(10)
		Self.UpdateSectionRow.addWidget(Self.UpdateProgramCheckBox)
		Self.LayoutFL.addRow(Self.UpdateSectionRow)

	# Window actions
	def CreateActions(Self):
		# Actions of global buttons
		Self.BottomBar.OkPB.clicked.connect(Self.aGuiAccepted)
		Self.BottomBar.CancelPB.clicked.connect(Self.close)
		Self.InfoD.OkPB.clicked.connect(Self.close)
		Self.InfoD.OkPB.clicked.connect(Self.InfoD.close)

		# Actions of form widgets
		Self.TmxNameLineEdit.textChanged.connect(lambda: Self.TextInputCheck(Self.TmxNameLineEdit))
		Self.MpConfigNameLineEdit.textChanged.connect(lambda: Self.TextInputCheck(Self.MpConfigNameLineEdit, Self.ProgramNameLineEdit))
		Self.ProgramNameLineEdit.textChanged.connect(lambda: Self.TextInputCheck(Self.ProgramNameLineEdit, Self.MpConfigNameLineEdit))

	# Text inputs condition check
	def TextInputCheck(Self, TextInput1: QLineEdit, TextInput2: QLineEdit = None):
		if (TextInput1.text() == ""):
			TextInput1.setStyleSheet("QLineEdit{background:#661111;}")
		else:
			TextInput1.setStyleSheet("")

		if TextInput2 != None:
			if (TextInput2.text() == ""):
				TextInput2.setStyleSheet("QLineEdit{background:#661111;}")
			else:
				TextInput2.setStyleSheet("")

			if (TextInput1.text() == TextInput2.text()):
				TextInput1.setStyleSheet("QLineEdit{background:#661111;}")
				TextInput2.setStyleSheet("QLineEdit{background:#661111;}")

	# GUI was accepted by OK button
	def aGuiAccepted(Self):
		if (Self.TmxNameLineEdit.text() != "") and (Self.MpConfigNameLineEdit.text() != "") and (Self.ProgramNameLineEdit.text() != "") and (Self.MpConfigNameLineEdit.text() != Self.ProgramNameLineEdit.text()):
			UserData["Configuration"] = Self.ConfigComboBox.currentText()
			UserData["Debug"] = Self.DebugPushButton.isChecked()
			UserData["UpdateTmx"] = Self.UpdateTmxCheckBox.isChecked()
			UserData["UpdateMpConfig"] = Self.UpdateMpConfigCheckBox.isChecked()
			UserData["UpdateProgram"] = Self.UpdateProgramCheckBox.isChecked()
			UserData["TmxName"] = Self.TmxNameLineEdit.text()
			UserData["MpConfigName"] = Self.MpConfigNameLineEdit.text()
			UserData["ProgramName"] = Self.ProgramNameLineEdit.text()
			
			with open(UserDataPath, "wb") as CreateAlarmsSettings:
				pickle.dump(UserData, CreateAlarmsSettings)
				
			Self.InfoD.MessageL.setText("The configuration has been set.")
			ShowAdjusted(Self.InfoD)

	# State of the window changed
	def changeEvent(Self, Event: QEvent):
		if Event.type() == Event.WindowStateChange:
			Self.TitleBar.windowStateChanged(Self.windowState())

	# Size of the window changed
	def resizeEvent(Self, Event: QEvent):
		Self.TitleBar.resize(Self.width(), Self.TitleBar.height())
		Self.MainGB.setGeometry(0, Self.TitleBar.height(), Self.width(), Self.height() - Self.TitleBar.height())

# Window title bar
class TitleBar(QWidget):
	ClickPosition = None

	# Initialization of the title bar
	def __init__(Self, Parent, WindowTitle, TitleColor, UseMinButton, UseMaxButton, UseCloseButton):
		super(TitleBar, Self).__init__(Parent)

		# Title bar layout
		Layout = QHBoxLayout(Self)
		Layout.setContentsMargins(int(8 * gSizeRatio), int(8 * gSizeRatio),int(8 * gSizeRatio),int(8 * gSizeRatio))
		Layout.addStretch()

		# Label title
		Self.Title = QLabel(WindowTitle, Self, alignment = Qt.AlignCenter)
		Style = "background-color: ReplaceColor; color: #cccccc; font: ReplaceTitleFontSizepx \"Bahnschrift SemiLight SemiConde\"; padding-top: 4px;".replace("ReplaceColor", TitleColor)
		Self.Title.setStyleSheet(FinishStyle(Style))
		Self.Title.adjustSize()

		# Appearance definition
		Style = Self.style()
		Self.ReferenceSize = Self.Title.height() - int(18 * gSizeRatio)
		Self.ReferenceSize += Style.pixelMetric(Style.PM_ButtonMargin) * 2
		Self.setMaximumHeight(Self.ReferenceSize + 2)
		Self.setMinimumHeight(Self.Title.height() + 12)

		# Tool buttons (Min, Normal, Max, Close)
		ButtonVisibility = {"min": UseMinButton, "normal": False, "max": UseMaxButton, "close": UseCloseButton}
		ButtonSize = QSize(Self.ReferenceSize, Self.ReferenceSize)
		for Target in ("min", "normal", "max", "close"):
			Button = QToolButton(Self, focusPolicy=Qt.NoFocus)
			Layout.addWidget(Button)
			Button.setFixedSize(ButtonSize)

			IconType = getattr(Style.StandardPixmap, "SP_TitleBar{}Button".format(Target.capitalize()))
			
			Button.setIcon(Style.standardIcon(IconType))
			
			if Target == "close":
				ColorNormal = "gray"
				ColorHover = "orangered"
			else:
				ColorNormal = "gray"
				ColorHover = "white"

			Button.setStyleSheet("QToolButton {{background-color: {};border: none; border-radius: 4px;}} QToolButton:hover {{background-color: {}}}".format(ColorNormal, ColorHover))

			Signal = getattr(Self, Target + "Clicked")
			Button.clicked.connect(Signal)

			setattr(Self, Target + "Button", Button)

			Button.setVisible(ButtonVisibility[Target])

	# State of the window changed
	def windowStateChanged(Self, State):
		Self.normalButton.setVisible(State == Qt.WindowMaximized)
		Self.maxButton.setVisible(State != Qt.WindowMaximized)

	# Mouse pressed event
	def mousePressEvent(Self, Event: QEvent):
		if Event.button() == Qt.LeftButton:
			Self.ClickPosition = Event.pos()

	# Mouse moved event
	def mouseMoveEvent(Self, Event: QEvent):
		if Self.ClickPosition is not None:
			Self.window().move(Self.window().pos() + Event.pos() - Self.ClickPosition)

	# Mouse released event
	def mouseReleaseEvent(Self, MouseEvent: QMouseEvent):
		Self.ClickPosition = None

	# Button Close clicked
	def closeClicked(Self):
		Self.window().close()

	# Button Maximize clicked
	def maxClicked(Self):
		Self.window().showMaximized()

	# Button Normal clicked
	def normalClicked(Self):
		Self.window().showNormal()

	# Button Minimize clicked
	def minClicked(Self):
		Self.window().showMinimized()

	# Size of the window changed
	def resizeEvent(Self, Event: QEvent):
		Self.Title.resize(Self.minButton.x() + Self.ReferenceSize * 3 + int(40 * gSizeRatio), Self.height())

# Window bottom button bar
class BottomBar(QWidget):
	# Initialization of the title bar
	def __init__(Self, Parent):
		super(BottomBar, Self).__init__(Parent)

		# Create bottom button box bar group box
		Self.BottomBarGB = QGroupBox()
		Self.BottomBarGB.setMaximumHeight(int(gAdjustedGuiSize["WidgetHeight"]) * 2)
		Style = """
		QGroupBox{
			background-color: transparent;
			border-top: 2px solid #222222;
			border-left: none;
			border-right: none;
			border-bottom: none;
			margin-top: 20px;
		}
			
		QToolTip {
			background-color: #eedd22;
		}

		QLabel {
			font: ReplaceFontSizepx \"Bahnschrift SemiLight SemiConde\";
			background-color: transparent;
		}

		QPushButton{
			background-color: #222222;
			color: #cccccc;
			width: ReplaceButtonWidthpx;
			height: ReplaceWidgetHeightpx;
			border-style: solid;
			border-radius: 8px;
		}

		QPushButton:hover{
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #373737, stop:0.505682 #373737, stop:1 #282828);
			color: #cccccc;
		}

		QPushButton:pressed{
			background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 #2d2d2d, stop:0.505682 #282828, stop:1 #2d2d2d);
			color: #ffffff;
		}
		"""
		Self.BottomBarGB.setStyleSheet(FinishStyle(Style))

		# Add buttons OK and Cancel to bottom bar
		BottomBarHBL = QHBoxLayout(Self.BottomBarGB)

		# Version label
		VersionL = QLabel("ⓘ " + SCRIPT_VERSION)
		VersionL.setToolTip("""To get more information about each row, hold the pointer on its label.
	\nSupport contacts
	michal.vavrik@br-automation.com
	adam.sefranek@br-automation.com
	\nVersion 2.1.0
	- PyGuiTemplate implemented
	\nVersion 2.0.2
	- Changes according to B&R Coding guidelines
	\nVersion 2.0.1
	- Once nested alarms path bug fixed
	- Supported properties change
	- Print of used configuration
	- Invalid property name bug fixed
	\nVersion 2.0.0
	- New system of finding alarm paths
	- Support of arrays (also defined by constants)
	\nVersion 1.2.0
	- Configuration of sections to update
	- Configuration of TMX, MpConfig and program name
	- Properties validity
	- Strings must be in quotation marks
	\nVersion 1.1.0
	- Bug with default alarm behavior fixed
	- Behavior.Monitoring.MonitoredPV bug fixed
	- Tags are taken from the graphics editor
	- Monitoring alarm types have no longer Set and Reset in the Alarms program
	- Path to user data changed to AppData\Roaming\BR\Scripts\CreateAlarms\\
	- Error mode added
	\nVersion 1.0.0
	- Script creation
	- Basic functions implemented""")
		BottomBarHBL.addWidget(VersionL, 0, Qt.AlignLeft)

		Self.OkPB = QPushButton("OK")
		BottomBarHBL.addWidget(Self.OkPB, 10, Qt.AlignRight)
		Self.CancelPB = QPushButton("Cancel")
		BottomBarHBL.addSpacing(10)
		BottomBarHBL.addWidget(Self.CancelPB, 0, Qt.AlignRight)

# Dialog for displaying info messages
class InfoDialog(QDialog):
	# Initialization of the dialog
	def __init__(Self):
		super(InfoDialog, Self).__init__()

		# Create title bar
		Self.TitleBar = TitleBar(Self, "Info", WINDOW_COLOR_STYLE, False, False, False)
		Self.setContentsMargins(0, Self.TitleBar.height(), 0, 0)

		# Set dialog styles
		Style = """
			QWidget{
				background-color:qlineargradient(spread:pad, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(0, 0, 0, 255), stop:1 rgba(20, 20, 20, 255));
				color:#cccccc;
				font: ReplaceFontSizepx \"Bahnschrift SemiLight SemiConde\";
			}

			QDialog{
				border: 2px solid ReplaceColor;
			}

			QLabel{
				background-color:transparent;
				color:#888888;
				qproperty-alignment: \'AlignVCenter | AlignCenter\';
				padding: 10px;
			}

			QPushButton{
				background-color: #222222;
				width: ReplaceButtonWidthpx;
				height: ReplaceWidgetHeightpx;
				border-style:solid;
				color:#cccccc;
				border-radius:8px;
			}

			QPushButton:hover{
				color:#cccccc;
				background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 rgba(55, 55, 55, 255), stop:0.505682 rgba(55, 55, 55, 255), stop:1 rgba(40, 40, 40, 255));
			}

			QPushButton:pressed{
				background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.517, y2:1, stop:0 rgba(45, 45, 45, 255), stop:0.505682 rgba(40, 40, 40, 255), stop:1 rgba(45, 45, 45, 255));
				color:#ffffff;
			}
			"""
		Self.setStyleSheet(FinishStyle(Style))

		# Set general dialog settings
		Self.setWindowTitle("Info")
		Self.setWindowFlag(Qt.FramelessWindowHint)
		Self.setGeometry(0, 0, 100, 100)
		Self.setModal(True)

		# Create widgets
		MainVBL = QVBoxLayout(Self)

		Self.MessageL = QLabel()
		MainVBL.addWidget(Self.MessageL)
		
		ButtonBoxHBL = QHBoxLayout()
		Self.OkPB = QPushButton()
		Self.OkPB.setText("OK")
		ButtonBoxHBL.addWidget(Self.OkPB)
		
		# Show dialog
		MainVBL.addLayout(ButtonBoxHBL)

	# Size of the window changed
	def resizeEvent(Self, Event: QEvent):
		Self.TitleBar.resize(Self.width(), Self.TitleBar.height())
		Self.TitleBar.Title.setMinimumWidth(Self.width())

# Dialog for displaying error messages
class ErrorDialog(QDialog):
	# Initialization of the dialog
	def __init__(Self, Messages):
		super(ErrorDialog, Self).__init__()

		# Create title bar
		Self.TitleBar = TitleBar(Self, "Error", "#6e1010", False, False, True)
		Self.setContentsMargins(0, Self.TitleBar.height(), 0, 0)

		# Set dialog styles
		Style = """
			QWidget{
				background-color:qlineargradient(spread:pad, x1:1, y1:0, x2:1, y2:1, stop:0 rgba(0, 0, 0, 255), stop:1 rgba(20, 20, 20, 255));
				color:#cccccc;
				font: ReplaceFontSizepx \"Bahnschrift SemiLight SemiConde\";
			}

			QDialog{
				border: 2px solid #6e1010;
			}

			QLabel{
				background-color:transparent;
				color:#888888;
				padding: 5px;
			}
			"""
		Self.setStyleSheet(FinishStyle(Style))

		# Set general dialog settings
		Self.setWindowTitle("Error")
		Self.setWindowFlag(Qt.FramelessWindowHint)
		Self.setGeometry(0, 0, 100, 100)

		# Create widgets
		DialogVBL = QVBoxLayout(Self)

		for Message in Messages:
			ErrorL = QLabel(Message)
			ErrorL.setOpenExternalLinks(True)
			DialogVBL.addWidget(ErrorL)
	
		# Show dialog
		ShowAdjusted(Self)

	# Size of the window changed
	def resizeEvent(Self, Event: QEvent):
		Self.TitleBar.resize(Self.width(), Self.TitleBar.height())
		Self.TitleBar.Title.setMinimumWidth(Self.width())

#####################################################################################################################################################
# Global functions
#####################################################################################################################################################
# Show widget with adjusted size
def ShowAdjusted(Widget: QWidget):
	# Adjust window size and position (must be twice to really adjust the size)
	Widget.adjustSize()
	Widget.adjustSize()
	Rectangle = Widget.frameGeometry()
	CenterPoint = QDesktopWidget().availableGeometry().center()
	Rectangle.moveCenter(CenterPoint)
	Widget.move(Rectangle.topLeft())
	Widget.show()

# Finish style with defined constants
def FinishStyle(Style: str):
	Style = Style.replace("ReplaceColor", WINDOW_COLOR_STYLE)
	for DefaultSizeElement in DEFAULT_GUI_SIZE:
		Style = Style.replace("Replace" + DefaultSizeElement, gAdjustedGuiSize[DefaultSizeElement])
	return Style

# Terminates the script
def TerminateScript():
	# Ouput window message
	print("--------------------------------- End of the script CreateAlarms ---------------------------------")
	sys.exit()

# Debug printing
def DebugPrint(Message, Data):
	if UserData["Debug"]: print(">> " + Message + " >> " + str(Data) + "\n")

# Finds file in directory and subdirectories, returns path to the FIRST found file and terminates script if file does not found and termination is required
# If *.extension FileName input (i.e. *.var) is specified, returns list of all occurrences of this extension
def FindFilePath(SourcePath, FileName, Terminate):
	if "*" in FileName: FilePath = []
	else: FilePath = ""
	EndLoop = False
	for DirPath, DirNames, FileNames in os.walk(SourcePath):
		if "*" in FileName:
			for File in FileNames:
				if File.endswith(FileName[1:]):
					FilePath.append(os.path.join(DirPath, File))
		else:
			for File in FileNames:
				if File == FileName:
					FilePath = os.path.join(DirPath, File)
					EndLoop = True
			if EndLoop:
				break
	if (FilePath == "" or FilePath == []) and Terminate:
		print("Error: File " + FileName + " does not exist.")
		TerminateScript()
	return FilePath

# Checks if file exists and terminates script if not
def IsFile(FilePath):
	if not os.path.isfile(FilePath):
		print("Error: File " + os.path.basename(FilePath) + " does not exist.")
		TerminateScript()
	return True

# Checks if directory exists and terminates script if not
def IsDir(DirPath):
	if not os.path.isdir(DirPath):
		print("Error: Directory " + DirPath + " does not exist.")
		TerminateScript()
	return True

# Get project info (project name, project path, path to logical)
def GetProjectInfo():
	CurrentPath = os.path.dirname(os.path.abspath(__file__))
	if (CurrentPath.find("Logical") == -1):
		print("Error: Directory 'Logical' does not exist.")
		ProjectName = ProjectPath = LogicalPath = ""
	else:
		# Get project path
		ProjectPath = CurrentPath[:CurrentPath.find("Logical") - 1]

		# Get project name
		ProjectName = os.path.basename(ProjectPath)

		# Get logical path
		LogicalPath = CurrentPath[:CurrentPath.find("Logical") + 7]

	return ProjectName, ProjectPath, LogicalPath

# Walk through all variables and data types and create list of alarms
def GetAlarms():
	"""
	Gets Alarm list from all variables and types

	Alarms [{
		Variable: ""
		Array: [Start, End]
		Path: [{
			Name: ""
			Type: ""
			Array: [Start, End]
			Description2: ""
			ParentType: ""
		}]
		Severity: ""
		Properties: [{
				Key: ""
				Value: ""
				Valid: False/True
				Tag: ""
		}]
	}]
	"""

	# Get all valid var and type files
	VarPaths = GetGlobalPaths("var")
	TypePaths = GetGlobalPaths("typ")

	# Get all global variables, constants and types
	GlobalVars, GlobalConsts = GetGlobalVars(VarPaths)
	GlobalTypes = GetGlobalTypes(TypePaths, GlobalConsts)

	# Look for all types with Error/Warning/Info in name
	AlarmTypes = []
	for GlobalType in GlobalTypes:
		if ("Error" in GlobalType["ParentType"]) or ("Warning" in GlobalType["ParentType"]) or ("Info" in GlobalType["ParentType"]):
			AlarmTypes.append(GlobalType["ParentType"])
	
	# Generate all alarm paths
	AlarmPaths = []
	GetPaths(AlarmTypes, GlobalTypes, AlarmPaths, True)
	for AlarmPath in AlarmPaths:
		AlarmPath.reverse()

	# Add global variables to alarm paths
	AlarmPaths = AddVarsToPaths(GlobalVars, GlobalTypes, AlarmPaths)

	# Create alarm list
	Alarms = CreateAlarms(GlobalTypes, AlarmPaths)

	# Alarm paths print
	if UserData["Debug"]:
		print("Paths to alarms:")
		for Index, Alarm in enumerate(Alarms):
			print(str(Index + 1) + ": " + str(PathToAlarm(Alarm)))
		print("\n")

	# Parse properties of alarms
	Alarms = ParseProperties(Alarms)

	DebugPrint("Alarms", Alarms)

	return Alarms

# Get all global paths excluding private files and files from Libraries
def GetGlobalPaths(Extension):
	# Get path to all .Extension files
	GlobalPaths = FindFilePath(LogicalPath, "*." + Extension, True)

	# Remove undesirable Extension files
	PathsToRemove = []
	for GlobalPath in GlobalPaths:
		FileName = os.path.basename(GlobalPath)
		DirName = os.path.dirname(GlobalPath)

		# Remove all "Libraries" files
		if "Libraries" in GlobalPath:
			PathsToRemove.append(GlobalPath)

		# Remove all Private files
		elif os.path.isfile(os.path.join(DirName, "Package.pkg")):
			PkgPath = os.path.join(DirName, "Package.pkg")
			PkgFile = open(PkgPath, "r")
			for Line in PkgFile:
				if (FileName in Line) and ("Private=\"true\"" in Line):
					PathsToRemove.append(GlobalPath)
		else:
			PathsToRemove.append(GlobalPath)

	GlobalPaths = list(set(GlobalPaths) - set(PathsToRemove))
	DebugPrint("All valid ." + Extension + " files", GlobalPaths)

	return GlobalPaths

# Get all global variables from VarPaths
def GetGlobalVars(VarPaths):
	"""
	Parses variables and constants from all valid global .var files.

	GlobalVars [{
		Name: ""
		Type: ""
		Array: [Start, End]
	}]

	GlobalConsts [{
		Name: ""
		Type: ""
		Value: ""
	}]
	"""
	GlobalVars = []
	GlobalConsts = []
	for VarPath in VarPaths:
		VarFile = open(VarPath, "r")
		VarText = VarFile.read()
		VarFile.close()
		VarStructures = re.findall(PATTERN_VAR_SECTION, VarText)
		for VarStructure in VarStructures:
			if (VarStructure[0] != '') or (VarStructure[2] != ''):
				if VarStructure[0] != '':
					Vars = re.findall(PATTERN_VARIABLE, VarStructure[0])
				else:
					Vars = re.findall(PATTERN_VARIABLE, VarStructure[2])
				for Var in Vars:
					if Var[0] != '':
						GlobalVars.append({"Name":Var[0], "Type":Var[2], "Array": ""})
					elif Var[3] != '':
						GlobalVars.append({"Name":Var[3], "Type":Var[6], "Array": [Var[4], Var[5]]})
			elif VarStructure[1] != '':
				Vars = re.findall(PATTERN_CONSTANT, VarStructure[1])
				for Var in Vars:
					if Var[1] in PERMITTED_TYPES_OF_ARRAY_CONSTANTS:
						GlobalConsts.append({"Name":Var[0], "Type":Var[1], "Value": Var[2]})
	
	GlobalConsts = GetConstsValue(GlobalConsts)
	GlobalVars = ReplaceConstsByNums(GlobalVars, GlobalConsts)
	DebugPrint("Global constants", GlobalConsts)
	DebugPrint("Global variables", GlobalVars)

	return GlobalVars, GlobalConsts

# Parse global types
def GetGlobalTypes(TypePaths, GlobalConsts):
	"""
	Parses types from all valid global .typ files.

	GlobalTypes [{
		Name: ""
		Type: ""
		Array: [Start, End]
		Description2: ""
		ParentType: ""
	}]
	"""
	GlobalTypes = []
	for TypePath in TypePaths:
		TypeFile = open(TypePath, "r")
		TypeText = TypeFile.read()
		TypeFile.close()
		TypeStructures = re.findall(PATTERN_STRUCTURE, TypeText)
		for TypeStructure in TypeStructures:
			Members = re.findall(PATTERN_MEMBER, TypeStructure[1])
			for Member in Members:
				if Member[0] != '':
					GlobalTypes.append({"Name": Member[0], "Type": Member[3], "Array": [Member[1], Member[2]], "Description2": Member[5], "ParentType": TypeStructure[0]})
				else:
					GlobalTypes.append({"Name": Member[6], "Type": Member[7], "Array": "", "Description2": Member[9], "ParentType": TypeStructure[0]})
		GlobalTypes = ReplaceConstsByNums(GlobalTypes, GlobalConsts)
	DebugPrint("Global types", GlobalTypes)

	return GlobalTypes

# Get value of all constants
def GetConstsValue(Consts):
	NotDoneConsts = []
	DoneConstsName = []
	DoneConstsValue = []
	for Index, Const in enumerate(Consts):
		try:
			if type(Const["Value"]) == str:
				Consts[Index]["Value"] = int(eval(Const["Value"]))
				DoneConstsName.append(Const["Name"])
				DoneConstsValue.append(Const["Value"])
		except:
			NotDoneConsts.append(Const)
	if NotDoneConsts != []:
		FoundZeroDoneConstants = True
		for Index, Const in enumerate(NotDoneConsts):
			InnerConsts = re.findall(PATTERN_CONSTANT_VALUE, Const["Value"])
			for InnerConst in InnerConsts:
				if InnerConst in DoneConstsName:
					FoundZeroDoneConstants = False
					# Consts[Find index of Const with Name in NotDoneConsts[Index]["Name"]]["Value"] = replace all InnerConst by values
					Consts[next((index for (index, d) in enumerate(Consts) if d["Name"] == NotDoneConsts[Index]["Name"]), None)]["Value"] = re.sub(r"\b%s\b" % InnerConst, str(DoneConstsValue[DoneConstsName.index(InnerConst)]), NotDoneConsts[Index]["Value"])
		if FoundZeroDoneConstants:
			for NotDoneConst in NotDoneConsts:
				InnerConsts = re.findall(PATTERN_CONSTANT_VALUE, NotDoneConst["Value"])
				for InnerConst in InnerConsts:
					if next((index for (index, d) in enumerate(NotDoneConsts) if d["Name"] == InnerConst), None) == None:
						print("Error: Constant " + InnerConst + " cannot be found.")
			TerminateScript()
		GetConstsValue(Consts)
		return Consts
	else:
		return Consts

# Replace list["Array"] defined with onstants by numbers and convert strings to ints
def ReplaceConstsByNums(List, GlobalConsts):
	for Index, Member in enumerate(List):
		if Member["Array"] != "":
			for i in (0,1):
				try:
					List[Index]["Array"][i] = int(Member["Array"][i])
				except:
					try:
						List[Index]["Array"][i] = GlobalConsts[next((index for (index, d) in enumerate(GlobalConsts) if d["Name"] == Member["Array"][i]), None)]["Value"]
					except:
						print("Error: Constant " + Member["Array"][i] + " in array of variable " + Member["Name"] + " cannot be found.")
						TerminateScript()
	return List

# Get all possible paths to alarm types
def GetPaths(AlarmTypes, GlobalTypes, AlarmPaths, FirstTime, Nesting = 0):
	Nesting += 1
	if Nesting >= UserData["MaxNesting"]:
		print("Warning: Recursive nesting in data types.")
		TerminateScript()
	Types = []
	AlarmTypes = list(set(AlarmTypes))
	for GlobalType in GlobalTypes:
		if GlobalType["Type"] in AlarmTypes:
			Types.append(GlobalType["ParentType"])
			if FirstTime:
				AlarmPaths.append([GlobalType])
			else:
				HelpAlarmPaths = []
				for IndexPath, AlarmPath in enumerate(AlarmPaths):
					for IndexMember, PathMember in enumerate(AlarmPath):
						if PathMember["ParentType"] == GlobalType["Type"]:
							if IndexMember == (len(AlarmPaths[IndexPath]) - 1):
								AlarmPaths[IndexPath].append(GlobalType)
							else:
								HelpList = AlarmPaths[IndexPath][:IndexMember + 1]
								HelpList.append(GlobalType)
								DoNotAppend = False
								for Path in AlarmPaths:
									if HelpList == Path[:IndexMember+2]:
										DoNotAppend = True
										break
								if not DoNotAppend:
									if HelpAlarmPaths == []:
										HelpAlarmPaths.append(HelpList)
									else:
										DoNotAppend = False
										for HelpPath in HelpAlarmPaths:
											if HelpList == HelpPath:
												DoNotAppend = True
												break
										if not DoNotAppend:
											HelpAlarmPaths.append(HelpList)
				if HelpAlarmPaths != []:
					for HelpPath in HelpAlarmPaths:
						AlarmPaths.append(HelpPath)
	if Types != []:
		GetPaths(Types, GlobalTypes, AlarmPaths, False, Nesting)

# Add global variables to the beginning of the paths
def AddVarsToPaths(GlobalVars, GlobalTypes, AlarmPaths):
	ExtendedPaths = []
	for GlobalVar in GlobalVars:
		PathsNumber = 0
		for AlarmPath in AlarmPaths:
			for IndexMember, PathMember in enumerate(AlarmPath):
				if GlobalVar["Type"] == PathMember["ParentType"]:
					PathsNumber += 1
					HelpPath = AlarmPath[IndexMember:]
					HelpPath.insert(0, GlobalVar)
					if HelpPath not in ExtendedPaths:
						ExtendedPaths.append(HelpPath)
		if PathsNumber == 0:
			if ("Error" in GlobalVar["Type"]) or ("Warning" in GlobalVar["Type"]) or ("Info" in GlobalVar["Type"]):
				for GlobalType in GlobalTypes:
					if GlobalVar["Type"] == GlobalType["ParentType"]:
						ExtendedPaths.append([GlobalVar])
						break
	return ExtendedPaths

# Create alarm list
def CreateAlarms(GlobalTypes, AlarmPaths):
	Alarms = []
	for AlarmPath in AlarmPaths:
		for GlobalType in GlobalTypes:
			if (GlobalType["ParentType"] == AlarmPath[-1]["Type"]) and (GlobalType["Type"] == "BOOL"):
				if ("Error" in GlobalType["ParentType"]):
					Severity = "Error"
				elif ("Warning" in GlobalType["ParentType"]):
					Severity = "Warning"
				elif ("Info" in GlobalType["ParentType"]):
					Severity = "Info"
				GlobalType["Description2"] = GlobalType["Description2"].replace("RequiredAndResettable", "3")
				GlobalType["Description2"] = GlobalType["Description2"].replace("RequiredAfterActive", "2")
				GlobalType["Description2"] = GlobalType["Description2"].replace("Required", "1")
				GlobalType["Description2"] = GlobalType["Description2"].replace("Disabled", "0")
				Alarms.append({"Variable": GlobalType["Name"], "Array": GlobalType["Array"], "Path": AlarmPath, "Severity": Severity, "Properties": GlobalType["Description2"]})
	return Alarms

# Parse properties of alarms
def ParseProperties(Alarms):
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
	for Member in Alarms:
		Pairs = re.findall(PATTERN_PAIR, Member["Properties"])
		Properties = []
		BehaviorFound = False

		for Pair in Pairs:
			Key = Pair[0]
			Value = Pair[1]
			
			if Value.startswith("\"") and Value.endswith("\""): 
				Value = Value[1:-1]
			
			if Key in PROPERTIES:
				BehaviorFound |= (Key == "Behavior")
				if "FALSE" in PROPERTIES[Key]["Validity"]:
					Value = Value.upper()
				Valid = Validity(Member["Variable"], Key, Value)
				Properties.append({"Key": Key, "Value": Value, "Valid": Valid, "Tag": PROPERTIES[Key]["Tag"], "ID": PROPERTIES[Key]["ID"]})
			else:
				print("Warning: Property '" + Key + "' of member '" + PathToAlarm(Member) +"' is not valid.")
				Properties.append({"Key": Key, "Value": Value, "Valid": False, "Tag": None, "ID": None})
		
		if not BehaviorFound and Properties:
			Key = "Behavior"
			Properties.append({"Key": Key, "Value": "EdgeAlarm", "Valid": True, "Tag": PROPERTIES[Key]["Tag"], "ID": PROPERTIES[Key]["ID"]})

		if Properties:
			Properties = sorted(Properties, key=lambda d: d["Key"])
			Member["Properties"] = Properties
	
	return Alarms

# Check validity of property value
def Validity(Name, Key, Value):
	Valid = False
	try:
		ValueNotInRangeText = "Warning: Value of property '" + Key + "' of member '" + Name + "' is not in valid range "
		if type(PROPERTIES[Key]["Validity"][0]) == int:
			if int(Value) in range(PROPERTIES[Key]["Validity"][0], PROPERTIES[Key]["Validity"][1] + 1):
				Valid = True
			else:
				print(ValueNotInRangeText + "<" + str(PROPERTIES[Key]["Validity"][0]) + "; " + str(PROPERTIES[Key]["Validity"][1]) + ">")

		elif type(PROPERTIES[Key]["Validity"][0]) == float:
			if (float(Value) >= PROPERTIES[Key]["Validity"][0]) and (float(Value) <= PROPERTIES[Key]["Validity"][1]):
				Valid = True
			else:
				print(ValueNotInRangeText + "<" + str(PROPERTIES[Key]["Validity"][0]) + "; " + str(PROPERTIES[Key]["Validity"][1]) + ">")

		elif type(PROPERTIES[Key]["Validity"][0]) == str:
			if Value in PROPERTIES[Key]["Validity"]:
				Valid = True
			else:
				if "FALSE" in PROPERTIES[Key]["Validity"]: print(ValueNotInRangeText + str(RANGE_BOOL))
				else: print(ValueNotInRangeText + str(PROPERTIES[Key]["Validity"]))
		elif PROPERTIES[Key]["Validity"][0] == None:
			Valid = True

	except:
		print("Warning: Wrong data type of property '" + Key + "' of member '" + Name + "'")

	return Valid

# Create alarm groups
def MpAlarmCreateGroup(Index: int, Name: str, Properties: list) -> et.Element:
	Group = et.Element("Group", {"ID": "["+str(Index)+"]"})
	Message = "{$Alarms/"+Name+"}"
	et.SubElement(Group, "Property", {"ID": "Name", "Value": Name})
	et.SubElement(Group, "Property", {"ID": "Message", "Value": Message})
	Properties = CreateTreeFromProperties(Properties)
	Properties = RemoveInvalidProperties(Properties)
	MpAlarmCreateNodes(Group, Properties)
	return Group

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
				if len(Keys) > 1:
					PropertyName = ".".join(Keys[0:Index+1])
				else:
					PropertyName = Key
				Parent = Parent.append(Node(Key, PROPERTIES[PropertyName]))
		Parent.append(Node(Last, Item))
	return Tree

# Remove invalid properties
def RemoveInvalidProperties(Properties: list) -> list:
	for Index, Item in enumerate(Properties.children):
		if ("Valid" in Item.data and Item.data["Valid"]) or ("Validity" in Item.data and Item.data["Validity"] == RANGE_NONE):
			RemoveInvalidProperties(Item)
		else:
			del(Properties.children[Index])
	return Properties

# Insert new configuration
def MpAlarmCreateNodes(Parent, Properties) -> et.Element:
	for Item in Properties:
		if Item.data:
			Attrib = {"ID": Item.data["ID"]}
			if "Value" in Item.data:
				Attrib["Value"] = Item.data["Value"]
			Element = et.Element(Item.data["Tag"], Attrib)
			MpAlarmCreateNodes(Element, Item)
			Parent.append(Element)
	return Parent

# Function for alarms set/reset text generation
def AlarmSetReset(SetResetText, Alarm, ProgramLanguage):
	AlarmName = ""
	ConfigNameCreation = ["\nbrsmemset(ADR(Name), 0, SIZEOF(Name));"]
	Tabs = "\n"
	NumberOfForLoops = 0
	for IndexMember, PathMember in enumerate(Alarm["Path"]):
		AlarmName += PathMember["Name"]
		if PathMember["Array"] != "":
			NumberOfForLoops += 1
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + PathMember["Name"] + "['));")
			ConfigNameCreation.append("\nbrsmemset(ADR(String), 0, SIZEOF(String));")
			ConfigNameCreation.append("\nbrsitoa(ArrayIndex" + str(NumberOfForLoops) + ", ADR(String));")
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR(String));")
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('].'));")
			AlarmName += "[ArrayIndex" + str(NumberOfForLoops) + "]."
			Tabs = "\n"
			for Index in range(NumberOfForLoops):
				Tabs += "\t"
			SetResetText += Tabs + "FOR ArrayIndex" + str(NumberOfForLoops) + " := " + str(PathMember["Array"][0]) + " TO " + str(PathMember["Array"][1]) + " DO"
		else:
			ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + PathMember["Name"] + ".'));")
			AlarmName += "."
	AlarmName += Alarm["Variable"]
	if Alarm["Array"] != "":
		NumberOfForLoops += 1
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + Alarm["Variable"] + "['));")
		ConfigNameCreation.append("\nbrsmemset(ADR(String), 0, SIZEOF(String));")
		ConfigNameCreation.append("\nbrsitoa(ArrayIndex" + str(NumberOfForLoops) + ", ADR(String));")
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR(String));")
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR(']'));")
		AlarmName += "[ArrayIndex" + str(NumberOfForLoops) + "]"
		Tabs = "\n"
		for Tab in range(NumberOfForLoops):
			Tabs += "\t"
		SetResetText += Tabs + "FOR ArrayIndex" + str(NumberOfForLoops) + " := " + str(Alarm["Array"][0]) + " TO " + str(Alarm["Array"][1]) + " DO"
	else:
		ConfigNameCreation.append("\nbrsstrcat(ADR(Name), ADR('" + Alarm["Variable"] + "'));")
	Tabs += "\t"

	ConfigName = ""
	BeforeStatic = False
	for Line in ConfigNameCreation:
		if "ADR('" in Line:
			if not BeforeStatic:
				ConfigName += Line
			else:
				ConfigName = ConfigName[:ConfigName.rfind("')")] + Line[Line.find("ADR('") + 5:Line.find("')")] + ConfigName[ConfigName.rfind("')"):]
			BeforeStatic = True
		else:
			ConfigName += Line
			BeforeStatic = False

	ConfigName = ConfigName.replace("\n", Tabs + "\t")
	ConfigName = ConfigName.replace("brsstrcat", "brsstrcpy", 1)

	if NumberOfForLoops != 0:
		SetResetText += Tabs + "IF (" + AlarmName + " <> Flag." + AlarmName + ") THEN"
		SetResetText += ConfigName
		SetResetText += Tabs + "\tIF (" + AlarmName + " > Flag." + AlarmName + ") THEN"
		SetResetText += Tabs + "\t\tMpAlarmXSet(gAlarmXCore, Name);"
		SetResetText += Tabs + "\tELSE"
		SetResetText += Tabs + "\t\tMpAlarmXReset(gAlarmXCore, Name);"
		SetResetText += Tabs + "\tEND_IF;"
	else:
		SetResetText += Tabs + "IF (" + AlarmName + " > Flag." + AlarmName + ") THEN"
		SetResetText += Tabs + "\tMpAlarmXSet(gAlarmXCore, '" + AlarmName + "');"
		SetResetText += Tabs + "END_IF;"
		SetResetText += Tabs + "IF (" + AlarmName + " < Flag." + AlarmName + ") THEN"
		SetResetText += Tabs + "\tMpAlarmXReset(gAlarmXCore, '" + AlarmName + "');"
	SetResetText += Tabs + "END_IF;"
	SetResetText += Tabs + "Flag." + AlarmName + "\t:= " + AlarmName + ";"

	for Index in range(NumberOfForLoops):
		Tabs = Tabs[:-1]
		SetResetText += Tabs + "END_FOR;"
	SetResetText += "\n\t"
		
	# Convert ST to C
	if ProgramLanguage == LANGUAGE_C:
		# FOR replacement
		SetResetText = re.sub("([\t]*)FOR ([a-zA-Z0-9_]*) := ([0-9]*) TO ([0-9]*) DO", r"\1for (\2 = \3; \2 <= \4; \2++)\n\1{", SetResetText)
		# IF replacement
		SetResetText = re.sub("([\t]*)IF \(([a-zA-Z0-9_.\[\]]*) ([<>=]*) ([a-zA-Z0-9_.\[\]]*)\) THEN", r"\1if (\2 \3 \4)\n\1{", SetResetText)
		SetResetText = re.sub("END_[a-zA-Z0-9_]*;", "}", SetResetText)
		# END_XXX occurrances
		SetResetText = re.sub("([\t]*)ELSE", r"\1}\n\1else\n\1{", SetResetText)
		# Other
		SetResetText = SetResetText.replace("'", "\"")
		SetResetText = SetResetText.replace(":= ", "= ")
		SetResetText = SetResetText.replace("<>", "!=")
		SetResetText = SetResetText.replace("(gAlarmXCore", "(&gAlarmXCore")
		SetResetText = SetResetText.replace("ADR", "(UDINT)&")
		SetResetText = SetResetText.replace("SIZEOF", "sizeof")

	return SetResetText, NumberOfForLoops

# Prebuild mode function
def Prebuild():

	DebugPrint("User settings", UserData)

	# Update Tmx file
	if UserData["UpdateTmx"]: UpdateTmx()

	# Update mpalarmxcore file
	if UserData["UpdateMpConfig"]: UpdateMpalarmxcore()

	# Update program file
	if UserData["UpdateProgram"]: UpdateProgram()

# Creates all paths to one alarm with all possible array values
def CreateNames(Alarm):
	Names = [""]
	FirstTime = True
	for PathMember in Alarm["Path"]:
		for Index, Name in enumerate(Names):
			if FirstTime:
				Names[Index] += PathMember["Name"]
				FirstTime = False
			else:
				Names[Index] += "." + PathMember["Name"]
		if PathMember["Array"] != "":
			Names = CreateArrays(Names, PathMember["Array"])
	for Index, Name in enumerate(Names):
		Names[Index] += "." + Alarm["Variable"]
	if Alarm["Array"] != "":
		Names = CreateArrays(Names, Alarm["Array"])
	return Names

# Expand paths with arrays
def CreateArrays(Names, Array):
	NewNames = []
	for Name in Names:
		for IndexArray in range(Array[0] - 1, Array[1]):
			NewNames.append(Name + "[" + str(IndexArray + 1) + "]")
	return NewNames

# Return path to alarm with array ranges
def PathToAlarm(Alarm) -> str:
	Path = ""
	for PathMember in Alarm["Path"]:
		Path += PathMember["Name"] + str(PathMember["Array"]) + " > "
	Path += Alarm["Variable"] + str(Alarm["Array"])
	return Path

# Update TMX file
def UpdateTmx():
	#####################################################################################################################################################
	# Update Tmx file
	#####################################################################################################################################################

	# Ouput window message
	print("Updating " + UserData["TmxName"] + ".tmx file...")

	# Get alarm names list from TMX file
	TmxPath = FindFilePath(LogicalPath, UserData["TmxName"] + ".tmx", True)

	TmxTree = et.parse(TmxPath)
	TmxRoot = TmxTree.getroot()

	TmxAlarms = []
	for TmxItem in TmxRoot.findall(".//tu"):
		TmxAlarms.append(TmxItem.attrib["tuid"])
	DebugPrint("Tmx alarms", TmxAlarms)

	# Get alarm names list from Global.typ file
	TypAlarms = []
	for Alarm in Alarms:
		TypAlarms += CreateNames(Alarm)
	DebugPrint("Typ alarms", TypAlarms)

	# Compare alarm names lists
	NewAlarms = [x for x in TypAlarms if x not in set(TmxAlarms)]
	MissingAlarms = [x for x in TmxAlarms if x not in set(TypAlarms)]
	
	DebugPrint("New alarms", NewAlarms)
	DebugPrint("Missing alarms", MissingAlarms)

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
def UpdateMpalarmxcore():
	#####################################################################################################################################################
	# Update mpalarmxcore
	#####################################################################################################################################################

	# Ouput window message
	print("Updating " + UserData["MpConfigName"] + ".mpalarmxcore file...")

	# Create path to mpalarmxcore
	MpAlarmPath = FindFilePath(ConfigPath, UserData["MpConfigName"] + ".mpalarmxcore", True)

	# Load file
	IsFile(MpAlarmPath)

	MpAlarmTree = et.parse(MpAlarmPath)
	MpAlarmRoot = MpAlarmTree.getroot()

	# Remove old configuration
	# Parent = MpAlarmRoot.find(".//Group[@ID=\"mapp.AlarmX.Core.Configuration\"]")
	Parent = MpAlarmRoot.find(".//Element[@Type=\"mpalarmxcore\"]")
	for Group in Parent.findall(".//Group[@ID=\"mapp.AlarmX.Core.Configuration\"]"):
		Parent.remove(Group)

	MpAlarmList = et.Element("Group", {"ID": "mapp.AlarmX.Core.Configuration"})

	Index = 0
	for Alarm in Alarms:
		for Name in CreateNames(Alarm):
			Element = MpAlarmCreateGroup(Index, Name, Alarm["Properties"])
			Index += 1
			MpAlarmList.append(Element)

	Parent.append(MpAlarmList)

	# Save file
	MpAlarmTree.write(MpAlarmPath)

# Update program file
def UpdateProgram():
	#####################################################################################################################################################
	# Update alarms program
	#####################################################################################################################################################

	# Detect programming language
	if (FindFilePath(LogicalPath, UserData["ProgramName"] + EXTENSIONS[LANGUAGE_C], False) != ""):
		ProgramLanguage = LANGUAGE_C
	else:
		ProgramLanguage = LANGUAGE_ST
	
	# Ouput window message
	print("Updating " + UserData["ProgramName"] + EXTENSIONS[ProgramLanguage] + " file...")

	# Generate cyclic program
	ProgramPath = FindFilePath(LogicalPath, UserData["ProgramName"] + EXTENSIONS[ProgramLanguage], True)

	# Create whole automatically generated cyclic section and insert it to the file
	ProgramFile = open(ProgramPath, "r")
	ProgramText = ""
	ErrorLastVariableName = ""
	WarningLastVariableName = ""
	InfoLastVariableName = ""
	AutomaticSectionStartFound = False
	InAutomaticSection = False

	if ProgramLanguage == LANGUAGE_C:
		ProgramErrorText = "\t/********************************************* Errors *********************************************/"
		ProgramWarningText = "\n\t\n\t/******************************************** Warnings ********************************************/"
		ProgramInfoText = "\n\t\n\t/********************************************* Infos **********************************************/"
	elif ProgramLanguage == LANGUAGE_ST:
		ProgramErrorText = "\t(********************************************* Errors *********************************************)"
		ProgramWarningText = "\n\t\n\t(******************************************** Warnings ********************************************)"
		ProgramInfoText = "\n\t\n\t(********************************************* Infos **********************************************)"

	MaxNumberOfForLoops = 0
	for ProgramLine in ProgramFile:
		if not InAutomaticSection:
			ProgramText += ProgramLine
		if (ProgramLine.find("// START OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section start
			AutomaticSectionStartFound = True
			InAutomaticSection = True
			for Alarm in Alarms:
				SetResetNotValid = False
				for Property in Alarm["Properties"]:
					if Property["Key"] == "Behavior":
						if ("Monitoring" in Property["Value"]) or not Property["Valid"]:
							SetResetNotValid = True
							break
				if not SetResetNotValid:
					if Alarm["Severity"] == "Error":
						if not(ErrorLastVariableName == Alarm["Path"][0]["Name"]):
							ProgramErrorText += "\n\t// Global variable " + Alarm["Path"][0]["Name"]
						ProgramErrorText, NumberOfForLoops = AlarmSetReset(ProgramErrorText, Alarm, ProgramLanguage)
						ErrorLastVariableName = Alarm["Path"][0]["Name"]
					elif Alarm["Severity"] == "Warning":
						if not(WarningLastVariableName == Alarm["Path"][0]["Name"]):
							ProgramWarningText += "\n\t// Global variable " + Alarm["Path"][0]["Name"]
						ProgramWarningText, NumberOfForLoops = AlarmSetReset(ProgramWarningText, Alarm, ProgramLanguage)
						WarningLastVariableName = Alarm["Path"][0]["Name"]
					elif Alarm["Severity"] == "Info":
						if not(InfoLastVariableName == Alarm["Path"][0]["Name"]):
							ProgramInfoText += "\n\t// Global variable " + Alarm["Path"][0]["Name"]
						ProgramInfoText, NumberOfForLoops = AlarmSetReset(ProgramInfoText, Alarm, ProgramLanguage)
						InfoLastVariableName = Alarm["Path"][0]["Name"]
					
					if NumberOfForLoops > MaxNumberOfForLoops:
						MaxNumberOfForLoops = NumberOfForLoops

			ProgramText += ProgramErrorText + ProgramWarningText + ProgramInfoText

		elif (ProgramLine.find("// END OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section end
			InAutomaticSection = False
			ProgramText += "\n\t\n" + ProgramLine

	ProgramFile.close()
	if not AutomaticSectionStartFound:
		print("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
		TerminateScript()
	elif InAutomaticSection:
		print("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms" + EXTENSIONS[ProgramLanguage] + ".")
		TerminateScript()
	else:
		ProgramFile = open(ProgramPath,"w")
		ProgramFile.write(ProgramText)
		ProgramFile.close()
		
	# Check if necessary variables exist and create them if not
	AlarmsVarPath = FindFilePath(os.path.dirname(ProgramPath), UserData["ProgramName"] + ".var", True)
	AlarmsVarFile = open(AlarmsVarPath, "r")
	AlarmsVarContent = AlarmsVarFile.read()
	AlarmsVarText = "\nVAR"
	if not "Flag : FlagType;" in AlarmsVarContent:
		AlarmsVarText += "\n\tFlag : FlagType; (*Flag structure used for edge detection*)"
	if (MaxNumberOfForLoops > 0) and (not "Name : STRING[255];" in AlarmsVarContent):
		AlarmsVarText += "\n\tName : STRING[255]; (*Auxiliary string for composing alarms name*)"
	if (MaxNumberOfForLoops > 0) and (not "String : STRING[255];" in AlarmsVarContent):
		AlarmsVarText += "\n\tString : STRING[255]; (*Auxiliary string for converting numbers to string*)"
	for Index in range(MaxNumberOfForLoops):
		if not ("ArrayIndex" + str(Index + 1) + " : INT;") in AlarmsVarContent:
			AlarmsVarText += "\n\tArrayIndex" + str(Index + 1) + " : INT; (*Index for iteration in for loops*)"
		
	AlarmsVarText += "\nEND_VAR"
	if AlarmsVarText != "\nVAR\nEND_VAR":
		AlarmsVarFile.close()
		AlarmsVarFile = open(AlarmsVarPath, "a")
		AlarmsVarFile.write(AlarmsVarText)
	AlarmsVarFile.close()

	# Generate Flag type
	AutomaticSectionStartFound = False
	InAutomaticSection = False
	AlarmsTypText = ""
	AlarmsTypPath = FindFilePath(os.path.dirname(ProgramPath), UserData["ProgramName"] + ".typ", True)
	AlarmsTypFile = open(AlarmsTypPath, "r")
	for AlarmsTypLine in AlarmsTypFile:
		if not InAutomaticSection:
			AlarmsTypText += AlarmsTypLine
		if (AlarmsTypLine.find("// START OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section start
			AutomaticSectionStartFound = True
			InAutomaticSection = True

			# Local types generation
			# Get unique paths
			UniquePaths = []
			for Alarm in Alarms:
				if Alarm["Path"] not in UniquePaths:
					UniquePaths.append(Alarm["Path"])

			LocalTypes = ["\nTYPE\n\tFlagType : STRUCT  (*Flag structure used for edge detection*)"]
			for UniquePath in UniquePaths:
				for IndexMember, Member in enumerate(UniquePath):
					if IndexMember == 0:
						if not Member["Name"] in LocalTypes[0]:
							if Member["Array"] != "":
								TypeFormat = "ARRAY[" + str(Member["Array"][0]) + ".." + str(Member["Array"][1]) + "]OF "
							else:
								TypeFormat = ""
							if (IndexMember + 1) != len(UniquePath):
								TypeFormat += Member["Type"][:-4] + "FlagType;"
							else:
								TypeFormat += Member["Type"] + ";"
							LocalTypes[0] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
					else:
						for IndexType, LocalType in enumerate(LocalTypes):
							if Member["Array"] != "":
								TypeFormat = "ARRAY[" + str(Member["Array"][0]) + ".." + str(Member["Array"][1]) + "]OF "
							else:
								TypeFormat = ""
							if (IndexMember + 1) != len(UniquePath):
								TypeFormat += Member["Type"][:-4] + "FlagType;"
							else:
								TypeFormat += Member["Type"] + ";"
							ParentTypeFormat = Member["ParentType"][:-4] + "FlagType"
							if ParentTypeFormat + " : STRUCT" in LocalType:
								if not Member["Name"] + " : " + TypeFormat in LocalTypes[IndexType]:
									if Member["Array"] != "":
										LocalTypes[IndexType] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
									else:
										LocalTypes[IndexType] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
								break
							elif (IndexType + 1) == len(LocalTypes):
								LocalTypes.append("\n\t" + ParentTypeFormat + " : STRUCT")
								if Member["Array"] != "":
									LocalTypes[IndexType + 1] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
								else:
									LocalTypes[IndexType + 1] += "\n\t\t" + Member["Name"] + " : " + TypeFormat
								break
			if (len(LocalTypes) == 1) and (LocalTypes[0] == "\nTYPE\n\tFlagType : STRUCT"):
				LocalTypes[0] += "\n\t\tNew_Member : USINT;"
			for LocalType in LocalTypes:
				AlarmsTypText += LocalType + "\n\tEND_STRUCT;"
			AlarmsTypText += "\nEND_TYPE"

		elif (AlarmsTypLine.find("// END OF AUTOMATIC CODE GENERATION //") != -1): # Automatic generation section end
			InAutomaticSection = False
			AlarmsTypText += "\n\n" + AlarmsTypLine

	AlarmsTypFile.close()
	if not AutomaticSectionStartFound:
		print("Error: Start of automatically generated section not found. Insert comment // START OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
		TerminateScript()
	elif InAutomaticSection:
		print("Error: End of automatically generated section not found. Insert comment // END OF AUTOMATIC CODE GENERATION // to Alarms.typ.")
		TerminateScript()
	else:
		AlarmsTypFile = open(AlarmsTypPath,"w")
		AlarmsTypFile.write(AlarmsTypText)
		AlarmsTypFile.close()

#####################################################################################################################################################
# Main
#####################################################################################################################################################

# Get project info
ProjectName, ProjectPath, LogicalPath = GetProjectInfo()

# Script mode decision
if LogicalPath == "":
	# Logical path not found
	RunMode = MODE_ERROR

elif "-prebuild" in sys.argv:
	# Argument -prebuild found
	RunMode = MODE_PREBUILD

else:
	# Argument -prebuild not found
	RunMode = MODE_CONFIGURATION

if not(RunMode == MODE_ERROR):
	# Get path to user data
	UserDataPath = os.path.join(os.getenv("APPDATA"), "BR", "Scripts", "CreateAlarms", ProjectName)
	if not os.path.isdir(os.path.dirname(UserDataPath)):
		os.makedirs(os.path.dirname(UserDataPath))

	# Load user data
	try:
		with open(UserDataPath, "rb") as CreateAlarmsSettings:
			UserData = pickle.load(CreateAlarmsSettings)
	except:
		UserData = {"Configuration":"", "Debug": False, "UpdateTmx": True, "UpdateMpConfig": True, "UpdateProgram": True, "TmxName": "Alarms", "MpConfigName": "AlarmsCfg", "ProgramName": "Alarms", "MaxNesting": 15}

	if (len(UserData) != 9):
		UserData = {"Configuration":"", "Debug": False, "UpdateTmx": True, "UpdateMpConfig": True, "UpdateProgram": True, "TmxName": "Alarms", "MpConfigName": "AlarmsCfg", "ProgramName": "Alarms", "MaxNesting": 15}

	# Get selected config path
	ConfigPath = os.path.join(ProjectPath, "Physical", UserData["Configuration"])

# Run respective script mode
if RunMode == MODE_PREBUILD:
	
	# Ouput window message
	print("----------------------- Beginning of the script CreateAlarms " + SCRIPT_VERSION + " -----------------------")
	if UserData["Configuration"] != "":
		UsedConfiguration = UserData["Configuration"]
	else:
		UsedConfiguration = FindFilePath(ConfigPath, UserData["MpConfigName"] + ".mpalarmxcore", True)
		UsedConfiguration = UsedConfiguration[UsedConfiguration.find("Physical") + 9:]
		UsedConfiguration = UsedConfiguration[:UsedConfiguration.find("\\")]
	print("Used configuration: " + UsedConfiguration)

	# Get alarms from global variables and types
	Alarms = GetAlarms()

	Prebuild()

	# Ouput window message
	print("--------------------------------- End of the script CreateAlarms ---------------------------------")

else:
	# Make application
	Application = QApplication(sys.argv)

	# Get size ratio (get the width of the screen and divide it by 1920, because that's the size for which this GUI was designed)
	gSizeRatio = Application.primaryScreen().availableGeometry().width() / 1920
	# Calculate adjusted sizes
	for DefaultSizeElement in DEFAULT_GUI_SIZE:
		gAdjustedGuiSize[DefaultSizeElement] = str(DEFAULT_GUI_SIZE[DefaultSizeElement] * gSizeRatio)[:str(DEFAULT_GUI_SIZE[DefaultSizeElement] * gSizeRatio).find(".")]

	if RunMode == MODE_CONFIGURATION:
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
		
		Window = MainWindow()

	elif RunMode == MODE_ERROR:
		Window = ErrorDialog(["Directory Logical not found. Please copy this script to the LogicalView of your project."])
		
	sys.exit(Application.exec())
