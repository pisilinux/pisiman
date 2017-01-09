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

# System
import os
import tempfile

# Qt
import QTermWidget

from PyQt5.QtWidgets import QMessageBox, QMainWindow, QFileDialog, QListWidgetItem
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import pyqtSignal, QFile, Qt


# UI
from gui.ui.main import Ui_MainWindow

# Dialogs
from gui.languages import LanguagesDialog
from gui.packages import PackagesDialog
from gui.packagecollection import PackageCollectionDialog

# Progress Dialog
from gui.progress import Progress

# Repository tools
from repotools.packages import Repository, ExIndexBogus, ExPackageCycle, ExPackageMissing
from repotools.project import Project, ExProjectMissing, ExProjectBogus

import gettext
_ = lambda x:gettext.ldgettext("pardusman", x)

class PackageCollectionListItem(QListWidgetItem):
    def __init__(self, parent, collection, language):
        QListWidgetItem.__init__(self, parent)
        self.collection = collection
        self.setText(collection.translations[language][0])

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, args):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.title = "Pisiman"
        # Terminal

        self.terminal = QTermWidget.QTermWidget()
        self.terminal.setHistorySize(-1)
        self.terminal.setScrollBarPosition(2)
        self.terminal.setColorScheme(0)
        #self.terminal.setTerminalFont(QFont('Terminus'))
        self.terminalLayout.addWidget(self.terminal)
        self.terminal.show()

     #   self.collectionFrame.hide()

        # Arguments
        self.args = args

        # Project
        self.project = Project()

        # Package repository
        self.repo = None

        # Package Selection collections
        self.collections = None

        # File menu
        self.actionNew.triggered.connect(self.slotNew)
        self.actionOpen.triggered.connect(self.slotOpen)
        self.actionSave.triggered.connect(self.slotSave)
        self.actionSaveAs.triggered.connect(self.slotSaveAs)
        self.actionExit.triggered.connect(self.close)

        # Project menu
        self.actionUpdateRepo.triggered.connect(self.slotUpdateRepo)
        self.actionLanguages.triggered.connect(self.slotSelectLanguages)
        self.actionPackages.triggered.connect(self.slotSelectPackages)
        self.actionRootImagePackages.triggered.connect(self.slotSelectRootImagePackages)
        self.actionLivecdImagePackages.triggered.connect(self.slotSelectLivecdImagePackages)
        self.actionDesktopImagePackages.triggered.connect(self.slotSelectDesktopImagePackages)
        self.actionMakeImage.triggered.connect(self.slotMakeImage)
        self.actionMake_Repo.triggered.connect(self.slotMake_Repo)
        self.actionMake_Image.triggered.connect(self.slotMake_Image)
        self.actionMake_Squashfs.triggered.connect(self.slotMake_Squashfs)
        self.actionMake_Iso.triggered.connect(self.slotMake_Iso)

        # Browse buttons
        self.pushBrowseRepository.clicked.connect(self.slotBrowseRepository)
        self.pushBrowseWorkFolder.clicked.connect(self.slotBrowseWorkFolder)
        self.pushBrowsePluginPackage.clicked.connect(self.slotBrowsePluginPackage)
        self.pushBrowseConfigFiles.clicked.connect(self.slotBrowseConfigFiles)

        # Change Package Selection
      #  self.pushAddCollection.clicked.connect(self.slotAddPackageCollection)
       # self.pushModifyCollection.clicked.connect(self.slotModifyPackageCollection)
       # self.pushRemoveCollection.clicked.connect(self.slotRemovePackageCollection)
       # self.pushSetDefaultCollection.clicked.connect(self.slotSetDefaultCollection)
       # self.checkCollection.stateChanged[int].connect(self.slotShowPackageCollection)
       # self.listPackageCollection.itemClicked[QListWidgetItem].connect(self.slotClickedCollection)

        # Initialize
        self.initialize()

    def initialize(self):
        if len(self.args) == 2:
            self.slotOpen(self.args[1])

    def initializeRepo(self):
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return

    def slotNew(self):
        """
            "New" menu item fires this function.
        """
        self.project = Project()
        self.loadProject()

    def slotOpen(self, filename=None):
        """
            "Open..." menu item fires this function.
        """
        if not filename:
            filename = QFileDialog.getOpenFileName(self, _("Select project file"), ".", "*.xml")
            filename=filename[0]
        if filename:
            self.project = Project()
            
            try:
                self.project.open(filename)
            except ExProjectMissing:
                QMessageBox.warning(self, self.title, _("Project file is missing."))
                return
            except ExProjectBogus:
                QMessageBox.warning(self, self.title, _("Project file is corrupt."))
                return
            self.loadProject()

    def slotSave(self):
        """
            "Save" menu item fires this function.
        """
        if self.project.filename:
            self.updateProject()
            self.project.save()
        else:
            self.slotSaveAs()

    def slotSaveAs(self):
        """
            "Save As..." menu item fires this function.
        """
        filename = QFileDialog.getSaveFileName(self, _("Save project"), os.getcwd(), "*.xml")
        filename=filename[0]
        if filename:
            self.project.filename = unicode(filename)
            self.slotSave()

    def slotBrowseRepository(self):
        """
            Browse repository button fires this function.
        """
        filename = QFileDialog.getOpenFileName(self, _("Select repository index"), ".", "pisi-index.xml*")
        filename=filename[0]
        if filename:
            filename = unicode(filename)
            if filename.startswith("/"):
                filename = "file://%s" % filename
            self.lineRepository.setText(filename)

    def slotBrowsePluginPackage(self):
        """
            Browse plugin package button fires this function.
        """
        filename = QFileDialog.getOpenFileName(self, _("Select plugin package"), ".", "*.pisi")
        filename=filename[0]
        if filename:
            self.linePluginPackage.setText(filename)

    def slotBrowseConfigFiles(self):
        """
            Browse release files button fires this function.
        """
        directory = QFileDialog.getExistingDirectory(self, "")
        if directory:
            self.lineConfigFiles.setText(directory)

    def slotBrowseWorkFolder(self):
        """
            Browse work folder button fires this function.
        """
        directory = QFileDialog.getExistingDirectory(self, "")
        if directory:
            self.lineWorkFolder.setText(directory)

    def slotAddPackageCollection(self):
        if not self.repo:
            self.initializeRepo()

        if not self.project.selected_languages:
            QMessageBox.warning(self, self.title, _("Installation Languages is not selected."))
            return

        dialog = PackageCollectionDialog(self, self.repo, self.project)
        if dialog.exec_():
            item = PackageCollectionListItem(self.listPackageCollection, dialog.collection, self.project.default_language)
            self.project.package_collections.append(item.collection)

            if self.listPackageCollection.count() == 1:
                item.collection.default = "True"


        self.updateCollection()

    def slotModifyPackageCollection(self):
        index = self.listPackageCollection.currentRow()
        item = self.listPackageCollection.item(index)
        if not self.repo:
            self.initializeRepo()

        dialog = PackageCollectionDialog(self, self.repo, self.project, item.collection)
        if dialog.exec_():
            if not item.collection._id == dialog.collection._id:
                item.setText(dialog.collection.translations[self.project.default_language][0])
            item.collection = dialog.collection

        self.updateCollection()


    def slotClickedCollection(self, item):
        if item.collection.default == "True":
            if not self.pushSetDefaultCollection.isChecked():
                self.pushSetDefaultCollection.setChecked(True)
        else:
            if self.pushSetDefaultCollection.isChecked():
                self.pushSetDefaultCollection.setChecked(False)

    def slotSetDefaultCollection(self):
        if self.listPackageCollection.currentItem() and not self.listPackageCollection.currentItem().collection.default:
            self.listPackageCollection.currentItem().collection.default = "True"
            currentIndex = self.listPackageCollection.currentRow()
            for index in xrange(self.listPackageCollection.count()):
                if index == currentIndex:
                    pass
                else:
                    self.listPackageCollection.item(index).collection.default = ""

            self.pushSetDefaultCollection.setChecked(True)


    def slotShowPackageCollection(self, state):
        if state == Qt.Checked:
            self.collectionFrame.show()
            self.actionPackages.setVisible(False)
        else:
            self.collectionFrame.hide()
            self.actionPackages.setVisible(True)

    def slotSelectLanguages(self):
        """
            "Languages..." menu item fires this function.
        """
        dialog = LanguagesDialog(self, self.project.selected_languages)
        if dialog.exec_():
            self.project.default_language = dialog.languages[0]
            self.project.selected_languages = dialog.languages

    def slotSelectPackages(self):
        """
            "Packages..." menu item fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return

        dialog = PackagesDialog(self, self.repo, self.project.selected_packages, self.project.selected_components)

        if dialog.exec_():
            self.project.selected_packages = dialog.packages
            self.project.selected_components = dialog.components
            self.project.all_packages = dialog.all_packages

    def slotSelectRootImagePackages(self):
        """
            "Root Image Packages..." menu item fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
            

        dialog = PackagesDialog(self, \
                                self.repo, \
                                self.project.selected_root_image_packages, \
                                self.project.selected_root_image_components)

        if dialog.exec_():
            self.project.selected_Root_image_packages = dialog.packages
            self.project.selected_root_image_components = dialog.components
            self.project.all_root_image_packages = dialog.all_packages
            
    def slotSelectDesktopImagePackages(self):
        """
            "Desktop Image Packages..." menu item fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return

        dialog = PackagesDialog(self, \
                                self.repo, \
                                self.project.selected_desktop_image_packages, \
                                self.project.selected_desktop_image_components)

        if dialog.exec_():
            self.project.selected_desktop_image_packages = dialog.packages
            self.project.selected_desktop_image_components = dialog.components
            self.project.all_desktop_image_packages = dialog.all_packages             
            
    def slotSelectLivecdImagePackages(self):
        """
            "Live cd Image Packages..." menu item fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return

        dialog = PackagesDialog(self, \
                                self.repo, \
                                self.project.selected_livecd_image_packages, \
                                self.project.selected_livecd_image_components)

        if dialog.exec_():
            self.project.selected_livecd_image_packages = dialog.packages
            self.project.selected_livecd_image_components = dialog.components
            self.project.all_livecd_image_packages = dialog.all_packages   
            

            
    def slotUpdateRepo(self):
        """
            Update repository button fires this function.
        """
        if not self.checkProject():
            return
        self.updateProject()
        self.updateRepo()

    def slotMakeImage(self):
        """
            Make image button fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
            
        if not self.checkImage():
            return            
            
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)

        # Konsole Mode
        # cmd = 'konsole --noclose --workdir "%s" -e "%s" make "%s"' % (os.getcwd(), app_path, temp_project.name)
        # subprocess.Popen(["xdg-su", "-u", "root", "-c", cmd])

        cmd = '%s make %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()
    
    def slotMake_Repo(self):
        """
            Make repo button fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
            
        if not self.checkImage():
            return              
            
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)


        cmd = '%s make-repo %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus() 
        
    def slotMake_Image(self):
        """
            Make repo button fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return

        if not self.checkImage():
            return   
        
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)


        cmd = '%s make-live %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()         
        
    def slotMake_Squashfs(self):
        """
            Make repo button fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
            
        if not self.checkImage():
            return  
        
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)


        cmd = '%s pack-live %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()             
        
    def slotMake_Iso(self):
        """
            Make iso button fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
            
        if not self.checkImage():
            return  
            
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)


        cmd = '%s make-iso %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()        

    def updateCollection(self):
        self.project.package_collections = []
        for index in xrange(self.listPackageCollection.count()):
            self.project.package_collections.append(self.listPackageCollection.item(index).collection)

    def checkProject(self):
        """
            Checks required fields for the project.
        """
        if not len(self.lineTitle.text()):
            QMessageBox.warning(self, self.windowTitle(),  _("Image title is missing."))
            return False
        
        if not len(self.lineRepository.text()):
            QMessageBox.warning(self, self.windowTitle(), _("Repository URL is missing."))
            return False
        
        if not len(self.lineWorkFolder.text()):
            QMessageBox.warning(self, self.windowTitle(),  _("Work folder is missing."))
            return False
        
        if not len(self.lineConfigFiles.text()):
            QMessageBox.warning(self, self.windowTitle(),  _("Config folder is missing."))
            return False
        
        return True
    
    def checkImage(self):   
        """
            Checks required step for project.
        """        
        
        if not self.project.selected_languages:
            QMessageBox.warning(self, self.title, _("Installation Languages is not selected."))
            return         
        
        if not self.project.all_root_image_packages:
            QMessageBox.warning(self, self.title, _("Root image packages not selected."))
            return 
        
        if not self.project.all_desktop_image_packages:
            QMessageBox.warning(self, self.title, _("Desktop image packages not selected."))
            return 
        
        if not self.project.all_livecd_image_packages:
            QMessageBox.warning(self, self.title, _("Live image packages not selected."))
            return         

        return True        
        
    def updateProject(self):
        """
            Updates project information.
        """
        self.project.title = unicode(self.lineTitle.text())
        self.project.repo_uri = unicode(self.lineRepository.text())
        self.project.work_dir = unicode(self.lineWorkFolder.text())
        self.project.config_files = unicode(self.lineConfigFiles.text())
        self.project.plugin_package = unicode(self.linePluginPackage.text())
        self.project.extra_params = unicode(self.lineParameters.text())
        self.project.type = ["None", "Lxdm", "Lightdm" ,"Mdm" ,"Sddm"][self.comboType.currentIndex()]
        self.project.squashfs_comp_type = ["xz", "gzip", "lzma", "lzo"][self.comboCompression.currentIndex()]


    def loadProject(self):
        """
            Loads project information.
        """
        self.lineTitle.setText(unicode(self.project.title))
        self.lineRepository.setText(unicode(self.project.repo_uri))
        self.lineWorkFolder.setText(unicode(self.project.work_dir))
        self.lineConfigFiles.setText(unicode(self.project.config_files))
        self.linePluginPackage.setText(unicode(self.project.plugin_package))
        self.lineParameters.setText(unicode(self.project.extra_params))
        self.comboType.setCurrentIndex(["None", "Lxdm", "Lightdm" ,"Mdm" ,"Sddm"].index(self.project.type))
        self.comboCompression.setCurrentIndex(["xz","gzip", "lzma", "lzo"].index(self.project.squashfs_comp_type))


    def updateRepo(self, update_repo=True):
        """
            Fetches package index and retrieves list of package and components.
        """
        # Progress dialog
        self.progress = Progress(self)
        # Update project
        self.updateProject()
        # Get repository
        try:
            self.repo = self.project.get_repo(self.progress, update_repo=update_repo)
        except ExIndexBogus, e:
            self.progress.finished()
            QMessageBox.warning(self, self.title, _("Unable to load package index. URL is wrong, or file is corrupt."))
            return False
        except ExPackageCycle, e:
            self.progress.finished()
            cycle = " > ".join(e.args[0])
            QMessageBox.warning(self, self.title, _("Package index has errors. Cyclic dependency found:\n  %s.") % cycle)
            return False
        except ExPackageMissing, e:
            self.progress.finished()
            QMessageBox.warning(self, self.title, _("Package index has errors. '%s' depends on non-existing '%s'.") % e.args)
            return False
        else:
            self.progress.finished()

        missing_components, missing_packages = self.project.get_missing()
        if len(missing_components):
            QMessageBox.warning(self, self.title, _("There are missing components: {}. Removing.".format(", ".join(missing_components))))
            for component in missing_components:
                if component in self.project.selected_components:
                    self.project.selected_components.remove(component)
                    self.project.selected_install_image_components.remove(component)
            return self.updateRepo(update_repo=False)
            #self.updateRepo(update_repo=False)

        if len(missing_packages):
            QMessageBox.warning(self, self.title, _("There are missing packages: {}. Removing.".format(", ".join(missing_packages))))
            for package in missing_packages:
                if package in self.project.selected_packages:
                    self.project.selected_packages.remove(package)
                    self.project.selected_install_image_packages.remove(package)
            return self.updateRepo(update_repo=False)

        self.progress.finished()

        return True
