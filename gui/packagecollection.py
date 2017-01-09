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
import hashlib
import os
import copy

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QFileDialog, QListWidgetItem, QMessageBox 
from PyQt5.QtGui import QPixmap

from gui.ui.packagecollection import Ui_PackageCollectionDialog
from gui.packages import PackagesDialog
from gui.languages import LANGUAGES
from repotools.packages import PackageCollection, PackageSet, random_id

import gettext
_ = lambda x:gettext.ldgettext("pardusman", x)

class PackageCollectionDialog(QDialog, Ui_PackageCollectionDialog):
    def __init__(self, parent, repo, project=None, collection=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.project = project
        self.parent = parent
        self.repo = repo
        self.repo_uri = os.path.join(repo.base_uri, repo.index_name)
        self.collection = None
        self.origCollection = None
        self.tmpCollection = None

        if collection:
            self.origCollection = collection
            self.tmpCollection = copy.deepcopy(collection)
        else:
            self.tmpCollection = PackageCollection(packages=PackageSet(self.repo_uri))

        self.titleText.textChanged[str].connect(self.titleChanged)
        self.languagesCombo.currentIndexChanged[int].connect(self.updateTranslations)
        self.descriptionText.textChanged.connect(self.descriptionChanged)
        self.packagesButton.clicked.connect(self.slotSelectPackages)
        self.selectIcon.clicked.connect(self.slotSelectIcon)
        self.clearIcon.clicked.connect(self.slotClearIcon)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.fillContent()

    def fillContent(self):
        self.titleText.clear()
        self.descriptionText.clear()
        if self.project.selected_languages:
            missingTranslations = set(self.project.selected_languages) - set(self.tmpCollection.translations)
            if missingTranslations:
                for code in missingTranslations:
                    self.tmpCollection.translations[code] = ("", "")
            for code in self.project.selected_languages:
                self.languagesCombo.addItem(LANGUAGES[code], unicode(code))
        else:
            self.project.default_language = "en_US"
            self.project.selected_languages.append("en_US")
            self.tmpCollection.translations["en_US"] = ("", "")
            self.languagesCombo.addItem(LANGUAGES["en_US"], unicode("en_US"))

        if self.tmpCollection.translations and self.tmpCollection.translations[self.project.default_language]:
            self.titleText.setText(unicode(self.tmpCollection.translations[self.project.default_language][0]))
            self.descriptionText.setPlainText(unicode(self.tmpCollection.translations[self.project.default_language][1]))

        if self.tmpCollection.icon:
            if os.path.exists(os.path.join(os.getcwd(), "icons", self.tmpCollection.icon)):
                self.icon.setPixmap(QPixmap(os.path.join(os.getcwd(), "icons", self.tmpCollection.icon)))

    def updateTranslations(self, currentIndex):
        code = unicode(self.languagesCombo.itemData(currentIndex))
        if code and self.tmpCollection.translations[code]:
            self.titleText.setText(unicode(self.tmpCollection.translations[code][0]))
            self.descriptionText.setPlainText(unicode(self.tmpCollection.translations[code][1]))

    def titleChanged(self, text):
        code = str(self.languagesCombo.itemData(self.languagesCombo.currentIndex()))
        if code and self.tmpCollection.translations[code]:
            translations = self.tmpCollection.translations[code]
            self.tmpCollection.translations[code] = (unicode(text), translations[1])

    def descriptionChanged(self):
        if not self.languagesCombo.itemData(self.languagesCombo.currentIndex()):
            return
        
        code = str(self.languagesCombo.itemData(self.languagesCombo.currentIndex()))
        if code and self.tmpCollection.translations[code]:
            translations = self.tmpCollection.translations[code]
            self.tmpCollection.translations[code] = (translations[0], unicode(self.descriptionText.toPlainText()))

    def accept(self):
        if self.origCollection:
            if self.origCollection != self.tmpCollection:
                self.tmpCollection._id = random_id()

        self.collection = self.tmpCollection
        QDialog.accept(self)

    def slotSelectIcon(self):
        iconPath = QFileDialog.getOpenFileName(self, _("Select Collection Icon"),
                                               os.path.join(os.getcwd(), "icons"),
                                               "*.png")[0]
        
        if iconPath:
            if self.tmpCollection:
                self.tmpCollection.icon = unicode(os.path.basename(unicode(iconPath)))
            self.icon.setPixmap(QPixmap(iconPath))

    def slotClearIcon(self):
        self.icon.setPixmap(QPixmap(0, 0))

    def slotSelectPackages(self):
        if self.tmpCollection.packages.selectedPackages and self.tmpCollection.packages.selectedComponents:
            dialog = PackagesDialog(self,
                                    self.repo,
                                    self.tmpCollection.packages.selectedPackages,
                                    self.tmpCollection.packages.selectedComponents)

            if dialog.exec_():
                self.tmpCollection.packages = PackageSet(self.repo_uri,\
                                                         dialog.components,\
                                                         dialog.packages,\
                                                         dialog.all_packages)

        else:
            dialog = PackagesDialog(self, self.repo)
            if dialog.exec_():
                self.tmpCollection.packages = PackageSet(self.repo_uri,\
                                                         dialog.components,\
                                                         dialog.packages,\
                                                         dialog.all_packages)

