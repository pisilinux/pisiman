#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2009, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

# Qt
from PyQt5.QtCore import QEventLoop
#from PyQt5.QtWidgets import QDialog

from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtCore import QCoreApplication

class Progress:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.application = None

    def started(self, title):
        self.dialog = QProgressDialog(title, "Stop", 0, 0, self.parent)
        self.dialog.setCancelButton(None)
        self.dialog.show()
        QCoreApplication.processEvents(QEventLoop.AllEvents)

    def progress(self, msg, percent):
        self.dialog.setLabelText(msg)
        # otherwise KProgressDialog automatically closes itself, sigh
        if percent < 100:
            self.dialog.setValue(percent)
        QCoreApplication.processEvents(QEventLoop.AllEvents)

    def finished(self):
        if self.dialog:
            self.dialog.done(0)
        self.dialog = None
