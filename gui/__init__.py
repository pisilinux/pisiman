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
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget,QApplication

# Main form
from gui.main import MainWindow


def gui(args):

    # Create applicatin
    app = QApplication(args)

    # Show main window
    mainWindow = MainWindow(args)
    mainWindow.show()

    app.setActiveWindow(mainWindow)

    # Close application if there's no window
    app.lastWindowClosed.connect(app.quit)

    # Go go go!
    app.exec_()
