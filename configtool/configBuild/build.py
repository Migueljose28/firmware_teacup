import wx.lib.newevent

try:
    import thread as _thread
except ImportError:
    import _thread
import os
import re
from os.path import isfile, join
from sys import platform
from .main import EVT_SCRIPT_UPDATE
from .main import SCRIPT_CANCELLED, SCRIPT_RUNNING, SCRIPT_FINISHED
from .scriptThread import ScriptThread
from .scriptTools import ScriptTools


class Build(wx.Dialog):
    def __init__(self, parent, settings, f_cpu, cpu):
        wx.Dialog.__init__(
            self,
            parent,
            wx.ID_ANY,
            "Build teacup",
            style=wx.RESIZE_BORDER + wx.DEFAULT_DIALOG_STYLE,
        )
        self.settings = settings
        self.SetFont(self.settings.font)
        self.root = self.settings.folder
        self.f_cpu = f_cpu
        self.cpu = cpu
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
        builddir = join(self.root, "build")
        if not os.path.exists(builddir):
            os.makedirs(builddir)
            self.log.AppendText("Directory %s created.\n\n" % builddir)

        self.compile()

    def compile(self):
        self.generateCompileScript()
        if len(self.script) == 0:
            self.log.AppendText("Nothing to compile!\n")
            self.active = False
        else:
            self.Bind(EVT_SCRIPT_UPDATE, self.compileUpdate)
            self.t = ScriptThread(self, self.script)
            self.active = True
            self.t.Start()

    def link(self):
        self.generateLinkScript()
        if len(self.script) == 0:
            self.log.AppendText("Nothing to link!\n")
            self.active = False
        else:
            self.Bind(EVT_SCRIPT_UPDATE, self.linkUpdate)
            t = ScriptThread(self, self.script)
            self.active = True
            t.Start()

    def report(self):
        self.script = []
        self.reportLines = []
        cmdpath = ScriptTools(self.settings).figureCommandPath("avr-objdump")
        elfpath = '"' + join(self.root, "build", "teacup.elf") + '"'
        cmd = cmdpath + " -h " + elfpath
        self.script.append(cmd)
        self.Bind(EVT_SCRIPT_UPDATE, self.reportUpdate)
        t = ScriptThread(self, self.script)
        self.active = True
        t.Start()

    def generateCompileScript(self):
        self.script = []
        cmdpath = ScriptTools(self.settings).figureCommandPath("avr-gcc")

        cfiles = [
            f
            for f in os.listdir(self.root)
            if isfile(join(self.root, f)) and f.endswith(".c")
        ]
        for f in cfiles:
            basename = f[:-2]
            ofile = basename + ".o"
            alfile = basename + ".al"
            opath = '"' + join(self.root, "build", ofile) + '"'
            alpath = '"' + join(self.root, "build", alfile) + '"'
            cpath = '"' + join(self.root, f) + '"'

            opts = self.settings.cflags
            opts = opts.replace("%ALNAME%", alpath)
            opts = opts.replace("%F_CPU%", self.f_cpu)
            opts = opts.replace("%CPU%", self.cpu)

            cmd = cmdpath + " -c " + opts + " -o " + opath + " " + cpath
            

            self.script.append(cmd)

    def generateLinkScript(self):
        self.script = []
        cmdpath = ScriptTools(self.settings).figureCommandPath("avr-gcc")

        # This is ugly:
        # Work around a problem of avr-ld.exe coming with Arduino 1.6.4 for
        # Windows. Without this it always drops this error message:
        #   collect2.exe: error: ld returned 5 exit status 255
        # Just enabling verbose messages allows ld.exe to complete without failure.
        if platform.startswith("win"):
            cmdpath += " -Wl,-V"

        ofiles = [
            '"' + join(self.root, "build", f) + '"'
            for f in os.listdir(join(self.root, "build"))
            if isfile(join(self.root, "build", f)) and f.endswith(".o")
        ]
        opath = " ".join(ofiles)
        elfpath = '"' + join(self.root, "build", "teacup.elf") + '"'
        hexpath = '"' + join(self.root, "teacup.hex") + '"'
        opts = self.settings.cflags
        opts = opts.replace("%ALNAME%", "teacup.elf")
        opts = opts.replace("%F_CPU%", self.f_cpu)
        opts = opts.replace("%CPU%", self.cpu)
        cmd = (
            cmdpath
            + " "
            + self.settings.ldflags
            + " "
            + opts
            + " -o "
            + elfpath
            + " "
            + opath
            + " -lm"
        )
        self.script.append(cmd)

        cmdpath = ScriptTools(self.settings).figureCommandPath("avr-objcopy")
        cmd = cmdpath + " " + self.settings.objcopyflags + " " + elfpath + " " + hexpath
        self.script.append(cmd)

    def compileUpdate(self, evt):
        if evt.msg is not None:
            self.log.AppendText(evt.msg + "\n")

        if evt.state == SCRIPT_RUNNING:
            pass

        if evt.state == SCRIPT_CANCELLED:
            self.active = False

            if self.cancelPending:
                self.EndModal(wx.ID_OK)

            self.log.AppendText("Build terminated abnormally.\n")

        if evt.state == SCRIPT_FINISHED:
            self.log.AppendText("Compile completed normally.\n\n")
            self.link()

    def linkUpdate(self, evt):
        if evt.msg is not None:
            self.log.AppendText(evt.msg + "\n")

        if evt.state == SCRIPT_RUNNING:
            pass
        if evt.state == SCRIPT_CANCELLED:
            self.log.AppendText("Link terminated abnormally.\n")
            self.active = False
        if evt.state == SCRIPT_FINISHED:
            self.log.AppendText("Link completed normally.\n")
            self.report()

    def reportUpdate(self, evt):
        if evt.state == SCRIPT_RUNNING:
            if evt.msg is not None:
                self.reportLines.append(evt.msg)
        if evt.state == SCRIPT_CANCELLED:
            self.log.AppendText(evt.msg + "\n")
            self.log.AppendText("Report terminated abnormally.\n")
            self.active = False
        if evt.state == SCRIPT_FINISHED:
            self.formatReport()
            self.log.AppendText("\nBuild completed normally.\n")
            self.active = False

    def formatReportLine(self, m, name, v168, v328, v644, v1280):
        t = m.groups()
        v = int(t[0], 16)
        self.log.AppendText(
            ("%12s:  %6d bytes   %6.2f%%   %6.2f%%" "   %6.2f%%   %6.2f%%\n")
            % (
                name,
                v,
                v / float(v168 * 1024) * 100.0,
                v / float(v328 * 1024) * 100.0,
                v / float(v644 * 1024) * 100.0,
                v / float(v1280 * 1024) * 100.0,
            )
        )

    def formatReport(self):
        reText = re.compile("\.text\s+([0-9a-f]+)")
        reBss = re.compile("\.bss\s+([0-9a-f]+)")
        reEEProm = re.compile("\.eeprom\s+([0-9a-f]+)")

        self.log.AppendText(
            "\n                   ATmega...     '168   '328(P)" "   '644(P)     '1280\n"
        )
        for l in self.reportLines:
            m = reText.search(l)
            if m:
                self.formatReportLine(m, "FLASH", 14, 30, 62, 126)
            else:
                m = reBss.search(l)
                if m:
                    self.formatReportLine(m, "RAM", 1, 2, 4, 8)
                else:
                    m = reEEProm.search(l)
                    if m:
                        self.formatReportLine(m, "EEPROM", 1, 2, 2, 4)

    def onExit(self, evt):
        if self.active:
            dlg = wx.MessageDialog(
                self,
                "Are you sure you want to cancel building?",
                "Build active",
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



