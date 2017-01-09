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

class PackageCollection(object):
    def __init__(self, uniqueTag="", icon="", title="", description="", packageSelection=None, languageSelection=None, default=""):
        self.uniqueTag = uniqueTag
        self.icon = icon
        self.title = title
        self.descriptionSelection = description
        self.packageSelection = packageSelection
        self.default =  default
        self.languageSelection = languageSelection

    def setDefault(self, default):
        self.default = default

class CollectionDescription(object):
    def __init__(self, description, translations={}):
        self.description = description
        self.translations = translations

    def addTranslation(self, code, translation):
        self.translations[code]=translation

class PackageSelection(object):
    def __init__(self, repoURI, selectedComponents=[], selectedPackages=[], allPackages=[]):
        self.repoURI = repoURI
        self.selectedComponents = selectedComponents
        self.selectedPackages = selectedPackages
        self.allPackages = allPackages

    def addSelectedComponent(self, component):
        self.selectedComponents.append(component)

    def addSelectedPackage(self, package):
        self.selectedPackages.append(package)

    def addPackage(self, package):
        self.allPackages.append(package)

class LanguageSelection(object):
    def __init__(self, defaultLanguage, languages=[]):
        self.defaultLanguage = defaultLanguage
        self.languages = languages

