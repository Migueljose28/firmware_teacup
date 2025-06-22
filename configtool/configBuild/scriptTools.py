from sys import platform
import os
from .main import TOOLPATHS_INSIDE_ARDUINO


class ScriptTools:
    def __init__(self, settings):
        self.settings = settings

    def figureCommandPath(self, baseCommand):
        findConf = False
        if baseCommand == "avrdude":
            findConf = True

        if platform.startswith("win"):
            baseCommand += ".exe"

        if self.settings.arduinodir:
            cmdpath = self.settings.arduinodir

            for pathOption in TOOLPATHS_INSIDE_ARDUINO:
                cmdpathTry = cmdpath
                for dir in pathOption.split("/"):
                    cmdpathTry = os.path.join(cmdpathTry, dir)
                cmdpathTry = os.path.join(cmdpathTry, baseCommand)
                if os.path.exists(cmdpathTry):
                    cmdpath = '"' + cmdpathTry + '"'
                    break

            if findConf:
                confpath = cmdpath.strip('"')
                exepos = confpath.rfind(".exe")
                if exepos >= 0:
                    confpath = confpath[0:exepos]
                confpath += ".conf"
                if not os.path.exists(confpath):
                    confpath = os.path.split(confpath)[0]
                    confpath = os.path.split(confpath)[0]
                    confpath = os.path.join(confpath, "etc")
                    confpath = os.path.join(confpath, "avrdude.conf")
                if os.path.exists(confpath):
                    cmdpath += ' -C "' + confpath + '"'

        else:
            cmdpath = baseCommand
            # No need to search avrdude.conf in this case.

        return cmdpath


