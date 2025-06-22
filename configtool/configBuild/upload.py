import wx.lib.newevent

try:
    import thread as _thread
except ImportError:
    import _thread
from .scriptThread import ScriptThread
from .main import EVT_SCRIPT_UPDATE
from .main import SCRIPT_FINISHED, SCRIPT_RUNNING, SCRIPT_CANCELLED
from .scriptTools import ScriptTools
from .build import join


class Upload(wx.Dialog):
    def __init__(self, parent, settings, f_cpu, cpu):
        wx.Dialog.__init__(
            self,
            parent,
            wx.ID_ANY,
            "Upload teacup",
            style=wx.RESIZE_BORDER + wx.DEFAULT_DIALOG_STYLE,
        )
        self.settings = settings
        self.SetFont(self.settings.font)
        self.root = self.settings.folder
        self.f_cpu = f_cpu
        self.cpu = cpu
        self.baud = self.settings.uploadspeed
        self.Bind(wx.EVT_CLOSE, self.onExit)
        self.cancelPending = False

        hsz = wx.BoxSizer(wx.HORIZONTAL)
        hsz.Add((10, 10))

        sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add((10, 10))

        tc = wx.TextCtrl(
            self, wx.ID_ANY, size=(900, 300), style=wx.TE_READONLY + wx.TE_MULTILINE
        )
        sz.Add(tc, 1, wx.EXPAND)
        f = wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        tc.SetFont(f)
        self.log = tc

        sz.Add((10, 10))
        hsz.Add(sz, 1, wx.EXPAND)
        hsz.Add((10, 10))

        self.SetSizer(hsz)

        self.Fit()
        self.generateUploadScript()
        if len(self.script) == 0:
            self.log.AppendText("Nothing to upload!\n")
            self.active = False
        else:
            self.Bind(EVT_SCRIPT_UPDATE, self.uploadUpdate)
            self.t = ScriptThread(self, self.script)
            self.active = True
            self.t.Start()

    def generateUploadScript(self):
        self.script = []
        cmdpath = ScriptTools(self.settings).figureCommandPath("avrdude")
        hexpath = '"' + join(self.root, "teacup.hex") + '"'

        cmd = cmdpath + " -c %s %s -b %s -p %s -P %s -U flash:w:%s:i" % (
            self.settings.programmer,
            self.settings.programflags,
            self.baud,
            self.cpu,
            self.settings.port,
            hexpath,
        )
        self.script.append(cmd)

    def uploadUpdate(self, evt):
        if evt.msg is not None:
            self.log.AppendText(evt.msg + "\n")

        if evt.state == SCRIPT_RUNNING:
            pass

        if evt.state == SCRIPT_CANCELLED:
            self.active = False

            if self.cancelPending:
                self.EndModal(wx.ID_OK)

            self.log.AppendText("Upload terminated abnormally.\n")

        if evt.state == SCRIPT_FINISHED:
            self.log.AppendText("Upload completed normally.\n")
            self.active = False

    def onExit(self, evt):
        if self.active:
            dlg = wx.MessageDialog(
                self,
                "Are you sure you want to cancel upload?",
                "Upload active",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION,
            )
            rc = dlg.ShowModal()
            dlg.Destroy()

            if rc == wx.ID_YES:
                self.cancelPending = True
                self.log.AppendText("Cancelling...\n")
                self.t.Stop()
            return

        self.EndModal(wx.ID_OK)
