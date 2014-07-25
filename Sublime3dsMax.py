""" Send maxscript files or codelines to 3ds Max.
"""
from __future__ import unicode_literals

import os
import sublime
import sublime_plugin

# Import depending on Sublime version
version = int(sublime.version())
ST3 = version > 3000 or version == ""
if ST3:
    from . import winapi
else:
    import winapi


# Create the tempfile in "Packages" (ST2) / "Installed Packages" (ST3)
TEMP = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    "Send_to_3ds_Max_Temp.ms"
)
NO_MXS_FILE = r"Sublime3dsMax: File is not a MAXScript file (*.ms, *.mcr)"
NO_TEMP = r"Sublime3dsMax: Could not write to temp file"
NOT_SAVED = r"Sublime3dsMax: File must be saved before sending to 3ds Max"
MAX_NOT_FOUND = r"Sublime3dsMax: Could not find a 3ds max instance."
RECORDER_NOT_FOUND = r"Sublime3dsMax: Could not find MAXScript Macro Recorder"

MAX_TITLE_IDENTIFIER = r"Autodesk 3ds Max"


def isMaxscriptFile(file):
    name, ext = os.path.splitext(file)
    return ext in (".ms", ".mcr")


def isPythonFile(file):
    name, ext = os.path.splitext(file)
    return ext in (".py")


def sendCmdToMax(cmd):
    """ Tries to find the 3ds Max window by title and
    the mini macrorecorder by class. Sends a string command
    and a return-key buttonstroke to it to evaluate the command.
    """
    gMainWindow = winapi.Window.find_window(MAX_TITLE_IDENTIFIER)
    gMiniMacroRecorder = None
    if gMainWindow is not None:
        gMiniMacroRecorder = gMainWindow.find_child(text=None, cls="MXS_Scintilla")
    else:
        sublime.error_message(MAX_NOT_FOUND)
    if gMiniMacroRecorder is not None:
        sublime.status_message('Send to 3ds Max: {cmd}'.format(**locals())[:-1])  # Cut ';'
        cmd = cmd.encode("utf-8")  # Needed for ST3!
        gMiniMacroRecorder.send(winapi.WM_SETTEXT, 0, cmd)
        gMiniMacroRecorder.send(winapi.WM_CHAR, winapi.VK_RETURN, 0)
        gMiniMacroRecorder = None
    else:
        sublime.error_message(RECORDER_NOT_FOUND)


def saveToTempFile(text):
    """ Stores code in a temporary maxscript file.
    """
    with open(TEMP, "w") as tempFile:
        if ST3:
            tempFile.write(text)
        else:
            text = text.encode("utf-8")
            tempFile.write(text)


class SendFileToMaxCommand(sublime_plugin.TextCommand):
    """ Sends the current file by using 'fileIn <file>'.
    """
    def run(self, edit):
        currentfile = self.view.file_name()
        if currentfile is None:
            sublime.error_message(NOT_SAVED)
            return

        if isMaxscriptFile(currentfile):
            cmd = 'fileIn (@"{currentfile}");'.format(**locals())
            sendCmdToMax(cmd)
        elif isPythonFile(currentfile):
            cmd = 'python.executefile (@"%s");' % currentfile
            sendCmdToMax(cmd)
        else:
            sublime.error_message(NO_MXS_FILE)


class SendSelectionToMaxCommand(sublime_plugin.TextCommand):
    """ Sends selected part of the file.
        Selection is extended to full line(s).
    """
    def run(self, edit):
        currentfile = self.view.file_name()
        for region in self.view.sel():
            text = None

            # If nothing selected, send single line
            if region.empty():
                line = self.view.line(region)
                text = self.view.substr(line)
                cmd = '{text};'.format(**locals())
                sendCmdToMax(cmd)

            # Else send all lines where something is selected
            # This only works by saving to a tempfile first,
            # as the mini macro recorder does not accept multiline input
            else:
                line = self.view.line(region)
                self.view.run_command("expand_selection", {"to": line.begin()})
                regiontext = self.view.substr(self.view.line(region))
                saveToTempFile(regiontext)
                if os.path.exists(TEMP):
                    if currentfile:
                        if isMaxscriptFile(currentfile):
                            cmd = 'fileIn (@"%s");' % TEMP
                    else:
                        cmd = 'python.executefile (@"%s");' % TEMP
                    sendCmdToMax(cmd)
                else:
                    sublime.error_message(NO_TEMP)
