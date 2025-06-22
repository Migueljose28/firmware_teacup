import wx.lib.newevent
from sys import platform

if platform.startswith("win"):
    from subprocess import STARTF_USESHOWWINDOW

(scriptEvent, EVT_SCRIPT_UPDATE) = wx.lib.newevent.NewEvent()
SCRIPT_RUNNING = 1
SCRIPT_FINISHED = 2
SCRIPT_CANCELLED = 3

TOOLPATHS_INSIDE_ARDUINO = [
    "hardware/tools/avr/bin/",
    "hardware/tools/",
]  # avrdude in Arduino 1.0.x
if platform.startswith("darwin"):
    # That's an OS property, the Applicaton Bundle hierarchy.
    pathsCopy = TOOLPATHS_INSIDE_ARDUINO
    TOOLPATHS_INSIDE_ARDUINO = []
    for path in pathsCopy:
        TOOLPATHS_INSIDE_ARDUINO.append("Contents/Resources/Java/" + path)
        TOOLPATHS_INSIDE_ARDUINO.append("Contents/Java/" + path)


