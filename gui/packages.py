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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QTreeWidgetItem
from PyQt5.QtGui import QBrush, QColor

# UI
from gui.ui.packages import Ui_PackagesDialog


class PackageWidgetItem(QTreeWidgetItem):
    def __init__(self, parent, package, component):
        QTreeWidgetItem.__init__(self, parent)
        self.package = package
        self.component = component
        self.required = False

        self.setCheckState(0, Qt.Unchecked)
        self.setText(0, package.name)
        self.setText(1, "%.3f" % (package.size / 1024.0 / 1024.0))
        self.setText(2, package.version)
        self.setText(3, package.release)

    def setChecked(self, checked):
        if checked:
            self.setCheckState(0, Qt.Checked)
        else:
            self.setCheckState(0, Qt.Unchecked)

    def isChecked(self):
        return self.checkState(0) == Qt.Checked

    def setRequired(self, required):
        self.required = required
        brush = QBrush()
        if required:
            brush.setColor(QColor(255, 0, 0))
        else:
            brush.setColor(QColor(0, 0, 0))
        self.setForeground(0, brush)

    def isRequired(self):
        return self.required


class ComponentWidgetItem(QTreeWidgetItem):
    def __init__(self, parent, component):
        QTreeWidgetItem.__init__(self, parent)
        self.component = component

        self.setCheckState(0, Qt.Unchecked)
        self.setText(0, component)

    def setChecked(self, checked):
        if checked:
            self.setCheckState(0, Qt.Checked)
        else:
            self.setCheckState(0, Qt.Unchecked)

    def isChecked(self):
        return self.checkState(0) == Qt.Checked


class PackagesDialog(QDialog, Ui_PackagesDialog):
    def __init__(self, parent, repo, packages=[], components=[]):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        # Package repository
        self.repo = repo

        # Selected packages/components
        self.packages = packages
        self.components = components
        self.all_packages = []

        # Search widget
        self.searchPackage.textChanged[str].connect(self.slotSearchPackage)

        # Ok/cancel buttons
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # Filter combo
        self.comboFilter.currentIndexChanged[int].connect(self.slotComboFilter)

        # Package/Component changes
        self.treeComponents.currentItemChanged[QTreeWidgetItem ,QTreeWidgetItem ].connect(self.slotSelectComponent)
        self.treeComponents.itemClicked[QTreeWidgetItem , int].connect(self.slotClickComponent)
        self.treePackages.currentItemChanged[QTreeWidgetItem ,QTreeWidgetItem ].connect(self.slotSelectPackage)
        self.treePackages.itemClicked[QTreeWidgetItem , int].connect(self.slotClickPackage)

        self.subcomponents = False
        self.component_only = False
        self.selected_component = None

        # Go go go!
        self.initialize()

    def initialize(self):
        """
            Fill in the blanks :)
        """
        # Packages
        for component, cpkgs in self.repo.components.items():
            for name in cpkgs:
                package = self.repo.packages[name]
                item = PackageWidgetItem(self.treePackages, package, component)
                if name in self.packages:
                    item.setChecked(True)

        # Resize columns to their contents
        for i in xrange(self.treePackages.columnCount()):
            self.treePackages.resizeColumnToContents(i)

        # Sort by package name in ascending order
        self.treePackages.sortByColumn(0, Qt.AscendingOrder)

        # Components
        for name in self.repo.components:
            item = ComponentWidgetItem(self.treeComponents, name)
            if name in self.components:
                item.setChecked(True)

        # Sort by component name in ascending order
        self.treeComponents.sortByColumn(0, Qt.AscendingOrder)

        # Draw selections
        self.updatePackages()

    def accept(self):
        self.packages = []
        self.components = []
        self.all_packages = []
        for index in xrange(self.treePackages.topLevelItemCount()):
            item = self.treePackages.topLevelItem(index)
            if item.isChecked():
                self.packages.append(item.package.name)
            if item.isRequired():
                self.all_packages.append(item.package.name)
        for index in xrange(self.treeComponents.topLevelItemCount()):
            item = self.treeComponents.topLevelItem(index)
            if item.isChecked():
                self.components.append(item.component)
        QDialog.accept(self)

    def slotSearchPackage(self, text):
        for index in xrange(self.treePackages.topLevelItemCount()):
            item = self.treePackages.topLevelItem(index)
            if item.text(0).__contains__(text):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def slotComboFilter(self, index):
        """
            Filter packages combo box fires this function.
        """
        selected_only = index == 1
        self.subcomponents = index == 3
        self.component_only = index == 2 or self.subcomponents
        self.filterPackages(selected_only=selected_only)

    def filterPackages(self, name=None, selected_only=False):
        """
            Filters package list.
        """
        for index in xrange(self.treePackages.topLevelItemCount()):
            item = self.treePackages.topLevelItem(index)
            if selected_only:
                if item.isChecked() or item.isRequired():
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            elif self.component_only:
                if not self.subcomponents and item.component == self.selected_component:
                    item.setHidden(False)
                elif self.subcomponents and item.component.startswith(self.selected_component):
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            else:
                item.setHidden(False)

    def slotSelectComponent(self, new, old):
        """
            Component selection fires this function.
        """
        self.selected_component = new.component
        self.filterPackages()

    def slotClickComponent(self, item):
        """
            Component click fires this function.
        """
        if item.isChecked():
            if item.component not in self.components:
                print item.text(0), "selected"
                self.components.append(item.component)
                self.updatePackages()
        else:
            if item.component in self.components:
                self.components.remove(item.component)
                self.updatePackages()

    def slotSelectPackage(self, new, old):
        """
            Package selection fires this function.
        """
        pass

    def slotClickPackage(self, item):
        """
            Package click fires this function.
        """
        if item.isChecked():
            if item.package.name not in self.packages:
                print item.text(0), "selected"
                self.packages.append(item.package.name)
                self.updatePackages()
        else:
            if item.package.name in self.packages:
                self.packages.remove(item.package.name)
                self.updatePackages()

    def updatePackages(self):
        """
            Updates package selections.
        """

        # Iterating all objects is a bad way to mark packages...

        size = 0
        required_packages = []
        for package in self.packages:
            for dep in self.repo.full_deps(package):
                if dep not in required_packages and dep != package:
                    required_packages.append(dep)

        for component in self.components:
            for package in self.repo.components[component]:
                for dep in self.repo.full_deps(package):
                    if dep not in required_packages:
                        required_packages.append(dep)

        for index in xrange(self.treePackages.topLevelItemCount()):
            item = self.treePackages.topLevelItem(index)
            selected = item.package.name in self.packages
            required = item.package.name in required_packages
            item.setChecked(selected)
            item.setRequired(required)
            if required or selected:
                size += item.package.size

        self.labelTotalSize.setText("%.3f MB" % (size / 1024.0 / 1024.0))
