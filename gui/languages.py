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
from PyQt5.QtWidgets import QDialog, QListWidgetItem

# UI
from gui.ui.languages import Ui_LanguagesDialog

LANGUAGES = {
    "ca_ES": "Catalan",
    "de_DE": "Deutsch",
    "en_US": "English",
    "es_ES": "Spanish",
    "fr_FR": "French",
    "hu_HU": "Hungarian",
    "hr_HR": "Croatian",
    "it_IT": "Italian",
    "nl_NL": "Dutch",
    "pl_PL": "Polish",
    "pt_BR": "Brazilian Portuguese",
    "ru_RU": "Russian",
    "sv_SE": "Svenska",
    "tr_TR": "Turkish",
}


class LanguageWidgetItem(QListWidgetItem):
    def __init__(self, code, label):
        QListWidgetItem.__init__(self)
        self.code = code
        self.label = label
        self.setText(label)


class LanguagesDialog(QDialog, Ui_LanguagesDialog):
    def __init__(self, parent, languages=[]):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        # Selected languages
        self.languages = languages

        # Ok/cancel buttons
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.upButton.clicked.connect(self.buttonUpClicked)
        self.downButton.clicked.connect(self.buttonDownClicked)
        self.addButton.clicked.connect(self.buttonAddClicked)
        self.removeButton.clicked.connect(self.buttonRemoveClicked)

        # Go go go!
        self.initialize()

    def buttonAddClicked(self):
        for item in self.availableListWidget.selectedItems():
            self.availableListWidget.takeItem(self.availableListWidget.row(item))
            self.selectedListWidget.insertItem(self.selectedListWidget.currentRow() + 1, item)
            self.selectedListWidget.setCurrentItem(item)

    def buttonRemoveClicked(self):
        for item in self.selectedListWidget.selectedItems():
            self.selectedListWidget.takeItem(self.selectedListWidget.row(item))
            self.availableListWidget.insertItem(self.selectedListWidget.currentRow() + 1, item)
            self.availableListWidget.setCurrentItem(item)

    def buttonUpClicked(self):
        index = self.selectedListWidget.currentRow()
        if index < 1:
            return
        else:
            item = self.selectedListWidget.item(index)
            self.selectedListWidget.takeItem(index)
            self.selectedListWidget.insertItem(index-1, item)
            self.selectedListWidget.setCurrentItem(item)

    def buttonDownClicked(self):
        index = self.selectedListWidget.currentRow()
        if index < 0 or index > self.selectedListWidget.count()-1:
            return
        else:
            item = self.selectedListWidget.item(index)
            self.selectedListWidget.takeItem(index)
            self.selectedListWidget.insertItem(index+1, item)
            self.selectedListWidget.setCurrentItem(item)

    def accept(self):
        self.languages = []
        selected = self.selectedListWidget
        for index in xrange(selected.count()):
            item = selected.item(index)
            self.languages.append(item.code)
        QDialog.accept(self)

    def initialize(self):
        selected = self.selectedListWidget
        available = self.availableListWidget
        for code in self.languages:
            item = LanguageWidgetItem(code, LANGUAGES[code])
            selected.addItem(item)
        for code, label in LANGUAGES.iteritems():
            if code not in self.languages:
                item = LanguageWidgetItem(code, label)
                available.addItem(item)
