import wx.lib.newevent

try:
    import thread as _thread
except ImportError:
    import _thread

import shlex
import subprocess
from sys import platform
from .main import STARTF_USESHOWWINDOW, scriptEvent
from .main import SCRIPT_CANCELLED, SCRIPT_RUNNING, SCRIPT_FINISHED


class ScriptThread:
    def __init__(self, win, script):
        self.win = win
        self.running = False
        self.cancelled = False
        self.script = script

    def Start(self):
        self.running = True
        self.cancelled = False
        _thread.start_new_thread(self.Run, ())

    def Stop(self):
        self.cancelled = True

    def IsRunning(self):
        return self.running

    def Run(self):
        if platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= STARTF_USESHOWWINDOW

        for cmd in self.script:
            evt = scriptEvent(msg=cmd, state=SCRIPT_RUNNING)
            wx.PostEvent(self.win, evt)
            args = shlex.split(str(cmd))
            try:
                if platform.startswith("win"):
                    p = subprocess.Popen(
                        args,
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE,
                        startupinfo=startupinfo,
                    )
                else:
                    p = subprocess.Popen(
                        args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE
                    )
            except:
                evt = scriptEvent(
                    msg="Exception occurred trying to run\n\n%s" % cmd,
                    state=SCRIPT_CANCELLED,
                )
                wx.PostEvent(self.win, evt)
                self.running = False
                return
            obuf = ""
            while not self.cancelled:
                o = p.stdout.read(1).decode("utf-8", "ignore")
                if o == "":
                    break
                if o == "\r" or o == "\n":
                    if obuf.strip() != "":
                        evt = scriptEvent(msg=obuf, state=SCRIPT_RUNNING)
                        wx.PostEvent(self.win, evt)
                    obuf = ""
                elif ord(o) < 32:
                    pass
                else:
                    obuf += o

            if self.cancelled:
                evt = scriptEvent(msg=None, state=SCRIPT_CANCELLED)
                wx.PostEvent(self.win, evt)
                p.kill()
                self.running = False
                p.wait()
                return

            rc = p.wait()
            if rc != 0:
                msg = "RC = " + str(rc) + " - Build terminated"
                evt = scriptEvent(msg=msg, state=SCRIPT_CANCELLED)
                wx.PostEvent(self.win, evt)
                self.running = False
                return

            evt = scriptEvent(msg="", state=SCRIPT_RUNNING)
            wx.PostEvent(self.win, evt)

        evt = scriptEvent(msg=None, state=SCRIPT_FINISHED)
        wx.PostEvent(self.win, evt)

        self.running = False
