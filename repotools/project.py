#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2010 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

import os
import re
import hashlib
import platform
import piksemel

import packages
from repotools.packages import PackageCollection, PackageSet

# no i18n yet
def _(x):
    return x

# Find out python version
PYTHON_VER = ".".join(platform.python_version_tuple()[0:2])

QT_PREFIX = "usr"
if os.path.exists("/usr/lib/qt5/libQtCore.so"):
    QT_PREFIX += "/lib/qt5"

default_exclude_list = """
var/cache/pisi/packages/
var/cache/pisi/archives/
var/tmp/pisi/
var/pisi/
tmp/pisi-root/
var/log/comar.log
var/log/pisi.log
/var/log/comar3/trace.log
root/.bash_history
"""

default_glob_excludes = (
    ( "usr/lib/python%s/" % PYTHON_VER, "*.pyc" ),
    ( "usr/lib/python%s/" % PYTHON_VER, "*.pyo" ),
    ( "usr/lib/pardus/", "*.pyc" ),
    ( "usr/lib/pardus/", "*.pyo" ),
    ( "var/db/comar/", "log.*" ),
)

class ExProject(Exception):
    pass

class ExProjectMissing(Exception):
    pass

class ExProjectBogus(Exception):
    pass

# Project class

class Project:
    def __init__(self):
        self.reset()

    def reset(self):
        self.filename = None
        self.title = ""
        self.work_dir = ""
        self.config_files = ""
        self.repo_uri = ""
        self.type = "None"
        self.squashfs_comp_type = "xz"
        self.extra_params = ""
        self.plugin_package = ""
        self.default_language = None
        self.selected_languages = []
        self.selected_components = []
        self.selected_packages = []
        self.all_packages = []
        self.package_collections = []
        self.missing_packages = []
        self.missing_components = []
        self.selected_root_image_components = []
        self.selected_root_image_packages = []
        self.selected_livecd_image_components = []
        self.selected_livecd_image_packages = []
        self.selected_desktop_image_components = []
        self.selected_desktop_image_packages = []
        self.all_root_image_packages = []

  
    def open(self, filename):
        # Open and parse project file filename
        try:
            doc = piksemel.parse(filename)
        except OSError, e:
            if e.errno == 2:
                raise ExProjectMissing
            raise
        except piksemel.ParseError:
            raise ExProjectBogus
        if doc.name() != "PisiManProject":
            raise ExProjectBogus

        self.reset()
        self.filename = filename



        # Fill in the properties from XML file
        self.title = doc.getTagData("Title")
        self.type = doc.getAttribute("type")
        self.squashfs_comp_type = doc.getAttribute("compression")

        self.plugin_package = doc.getTagData("PluginPackage")
        if not self.plugin_package:
            self.plugin_package = ""

        self.extra_params = doc.getTagData("ExtraParameters")
        if not self.extra_params:
            self.extra_params = ""
        self.work_dir = doc.getTagData("WorkDir")
        if not self.work_dir:
            self.work_dir = ""
            
        self.config_files = doc.getTagData("ConfigFiles")
        if not self.config_files:
            self.config_files = ""      
            
        def __packageSelection(node):
            # Fill in the packages
            selectedComponents = [ ]
            selectedPackages = [ ]
            allPackages = [ ]
            if node:
                repoURI = node.getAttribute("repo_uri")
                for tag in node.tags("SelectedComponent"):
                    selectedComponents.append(tag.firstChild().data())
                for tag in node.tags("SelectedPackage"):
                    selectedPackages.append(tag.firstChild().data())
                for tag in node.tags("Package"):
                    allPackages.append(tag.firstChild().data())
                #print repoURI, "\n", selectedComponents, "\n", selectedPackages, "\n", allPackages
                return (repoURI, selectedComponents, selectedPackages, allPackages)
            return None

        def __collectionTranslations(node):
            # Fill collection translations
            translations = {}
            if node:
                for translation in node.tags("Translation"):
                    translations[translation.getAttribute("language")]= (unicode(translation.getTagData("Title")),
                                                                         unicode(translation.getTagData("Description")))
                return translations
            return None

        def __languageSelection(node):
            # Fill the languages
            defaultLanguage = None
            selectedLanguages = []

            if node:
                defaultLanguage = node.getAttribute("default_language")
                for tag in node.tags("Language"):
                    selectedLanguages.append(tag.firstChild().data())

                if defaultLanguage not in selectedLanguages:
                    selectedLanguages.append(defaultLanguage)

                return (defaultLanguage, selectedLanguages)

            return None

        collectionsTag = doc.getTag("PackageCollections")
        if collectionsTag:
            for collection in collectionsTag.tags("PackageCollection"):
                default = collection.getAttribute("default")
                if not default:
                    default = ""

                # Reads Collection identifiers
                id = collection.getTagData("Id")
                icon = collection.getTagData("Icon")

                # Reads Collection Translations
                translations = __collectionTranslations(collection.getTag("Translations"))

                # Reads Collection Selected Packages
                uri, selectedcomponents, selectedpackages, allPackages = __packageSelection(collection.getTag("PackageSelection"))
                packages = PackageSet(uri, selectedcomponents, selectedpackages, allPackages)

                self.package_collections.append(PackageCollection(id, icon, translations, packages, default))

            # Hack for now.Change After multi repository support
            self.repo_uri = self.package_collections[0].packages.repoURI

            for collection in self.package_collections:
                collection.packages.selectedComponents.sort()
                collection.packages.selectedPackages.sort()
                collection.packages.allPackages.sort()
        else:
            packageSelectionTag = doc.getTag("PackageSelection")
            if packageSelectionTag:
                self.repo_uri, self.selected_components, self.selected_packages, self.all_packages= __packageSelection(packageSelectionTag)

            self.selected_components.sort()
            self.selected_packages.sort()
            self.all_packages.sort()

        languageSelectionTag = doc.getTag("LanguageSelection")
        if languageSelectionTag:
            self.default_language, self.selected_languages = __languageSelection(languageSelectionTag)
            
        rootImagePackagesTag = doc.getTag("RootImagePackages")
        if rootImagePackagesTag:
            uri, \
            self.selected_root_image_components, \
            self.selected_root_image_packages, \
            self.all_root_image_packages = __packageSelection(rootImagePackagesTag)

            self.selected_root_image_components.sort()
            self.selected_root_image_packages.sort()
            self.all_root_image_packages.sort()    
            
        desktopImagePackagesTag = doc.getTag("DesktopImagePackages")
        if desktopImagePackagesTag:
            uri, \
            self.selected_desktop_image_components, \
            self.selected_desktop_image_packages, \
            self.all_desktop_image_packages = __packageSelection(desktopImagePackagesTag)

            self.selected_desktop_image_components.sort()
            self.selected_desktop_image_packages.sort()
            self.all_desktop_image_packages.sort()       
            
        livecdImagePackagesTag = doc.getTag("LivecdImagePackages")
        if livecdImagePackagesTag:
            uri, \
            self.selected_livecd_image_components, \
            self.selected_livecd_image_packages, \
            self.all_livecd_image_packages = __packageSelection(livecdImagePackagesTag)

            self.selected_livecd_image_components.sort()
            self.selected_livecd_image_packages.sort()
            self.all_livecd_image_packages.sort()

          

    def save(self, filename=None):
        # Save the data into filename as pardusman project file
        doc = piksemel.newDocument("PisiManProject")

        doc.setAttribute("type", self.type)
        doc.setAttribute("compression", str(self.squashfs_comp_type))

        if self.title:
            doc.insertTag("Title").insertData(self.title)
        if self.work_dir:
            doc.insertTag("WorkDir").insertData(self.work_dir)
            
        if self.config_files:
            doc.insertTag("ConfigFiles").insertData(self.config_files)            
            
        if self.plugin_package:
            doc.insertTag("PluginPackage").insertData(self.plugin_package)
        if self.extra_params:
            doc.insertTag("ExtraParameters").insertData(self.extra_params)

        if self.package_collections:
            collections = doc.insertTag("PackageCollections")
            for collection in self.package_collections:
                packageCollection = collections.insertTag("PackageCollection")
                # Writes if collection is default
                if collection.default:
                    packageCollection.setAttribute("default", collection.default)

                # Writes Collection identifiers
                packageCollection.insertTag("Id").insertData(collection._id)
                packageCollection.insertTag("Icon").insertData(collection.icon)

                # Writes Translations
                translations = packageCollection.insertTag("Translations")
                for key, item in collection.translations.items():
                    translation = translations.insertTag("Translation")
                    translation.setAttribute("language", key)
                    translation.insertTag("Title").insertData(item[0])
                    translation.insertTag("Description").insertData(item[1])

                # Writes Packages
                packageSelection = packageCollection.insertTag("PackageSelection")
                # FIXME: ilker manap, self.repo_uri almasi gerek.
                packageSelection.setAttribute("repo_uri", self.repo_uri)
                for item in collection.packages.selectedComponents:
                    packageSelection.insertTag("SelectedComponent").insertData(item)
                for item in collection.packages.selectedPackages:
                    packageSelection.insertTag("SelectedPackage").insertData(item)
                for item in collection.packages.allPackages:
                    packageSelection.insertTag("Package").insertData(item)

        else:
           

            self.selected_components.sort()
            
            self.selected_packages.sort()
            
            self.all_packages.sort()


            package_selection = doc.insertTag("PackageSelection")
            package_selection.setAttribute("repo_uri", self.repo_uri)

            # Insert components if any
            
            for item in self.selected_root_image_components:
                package_selection.insertTag("SelectedComponent").insertData(item)  
                
            for item in self.selected_desktop_image_components:
                package_selection.insertTag("SelectedComponent").insertData(item)   
                
            for item in self.selected_livecd_image_components:
                package_selection.insertTag("SelectedComponent").insertData(item)
                

            for item in self.selected_root_image_packages:
                package_selection.insertTag("SelectedPackage").insertData(item)
                
            for item in self.selected_desktop_image_packages:
                package_selection.insertTag("SelectedPackage").insertData(item)  

            for item in self.selected_livecd_image_packages:
                package_selection.insertTag("SelectedPackage").insertData(item)   
                
            for item in self.all_root_image_packages:
                package_selection.insertTag("Package").insertData(item)    
                
            for item in self.all_desktop_image_packages:
                package_selection.insertTag("Package").insertData(item)

            for item in self.all_livecd_image_packages:
                package_selection.insertTag("Package").insertData(item)
                
                
        if self.all_root_image_packages:
            self.selected_root_image_components.sort()
            self.selected_root_image_packages.sort()
            self.all_root_image_packages.sort()

            package_selection = doc.insertTag("RootImagePackages")
            
            # Insert components if any
            for item in self.selected_root_image_components:
                package_selection.insertTag("SelectedComponent").insertData(item)

            for item in self.selected_root_image_packages:
                package_selection.insertTag("SelectedPackage").insertData(item)

            for item in self.all_root_image_packages:
                package_selection.insertTag("Package").insertData(item)
                
                
        if self.all_desktop_image_packages:
            self.selected_desktop_image_components.sort()
            self.selected_desktop_image_packages.sort()
            self.all_desktop_image_packages.sort()
             
            package_selection = doc.insertTag("DesktopImagePackages")
            
            # Insert components if any
            for item in self.selected_desktop_image_components:
                package_selection.insertTag("SelectedComponent").insertData(item)

            for item in self.selected_desktop_image_packages:
                package_selection.insertTag("SelectedPackage").insertData(item)

            for item in self.all_desktop_image_packages:
                package_selection.insertTag("Package").insertData(item)                

        if self.all_livecd_image_packages:
            self.selected_livecd_image_components.sort()
            self.selected_livecd_image_packages.sort()
            self.all_livecd_image_packages.sort()
             
            package_selection = doc.insertTag("LivecdImagePackages")
            
            # Insert components if any
            for item in self.selected_livecd_image_components:
                package_selection.insertTag("SelectedComponent").insertData(item)

            for item in self.selected_livecd_image_packages:
                package_selection.insertTag("SelectedPackage").insertData(item)

            for item in self.all_livecd_image_packages:
                package_selection.insertTag("Package").insertData(item)
                
                
        if self.default_language:
            # Set the default language
            langs = doc.insertTag("LanguageSelection")
            langs.setAttribute("default_language", self.default_language)

            # Insert other supported languages if any
            for item in self.selected_languages:
                langs.insertTag("Language").insertData(item)

        # Write the file
        if not filename:
            filename = self.filename
        f = file(filename, "w")
        f.write(doc.toPrettyString())
        f.close()

    def exclude_list(self):
        import fnmatch

        def _glob_exclude(lst, excludes):
            image_dir = self.image_dir()
            for exc in excludes:
                path = os.path.join(image_dir, exc[0])
                for root, dirs, files in os.walk(path):
                    for name in files:
                        if fnmatch.fnmatch(name, exc[1]):
                            lst.append(os.path.join(root[len(image_dir)+1:], name))


        temp = default_exclude_list.split()
        _glob_exclude(temp, default_glob_excludes)
        
        return temp

    def _get_dir(self, name, clean=False):
        dirname = os.path.join(self.work_dir, name)
        if os.path.exists(dirname):
            if clean:
                os.system('rm -rf "%s"' % dirname)
                os.makedirs(dirname)
        else:
            os.makedirs(dirname)
        return dirname

    def get_repo(self, console=None, update_repo=False):
        cache_dir = self._get_dir("repo_cache")
        repo = packages.Repository(self.repo_uri, cache_dir)
        repo.parse_index(console, update_repo)
        self.find_all_packages(repo)
        return repo

    def get_missing(self):
        return self.missing_components, self.missing_packages

    def find_all_packages(self, repo):
        self.missing_packages = []
        self.missing_components = []
        packages = []
        self.all_packages = []

        def collect(name):
            if name not in repo.packages:
                if name not in self.missing_packages:
                    self.missing_packages.append(name)
                return
            p = repo.packages[name]
            if name in packages:
                return
            packages.append(name)
            for dep in p.depends:
                collect(dep)

        if self.package_collections:
            for collection in self.package_collections:
                packages = []
                for component in collection.packages.selectedComponents:
                    if component not in repo.components:
                        if component not in self.missing_components:
                            self.missing_components.append(component)
                        return
                    for package in repo.components[component]:
                        collect(package)

                for package in collection.packages.selectedPackages:
                    collect(package)

                packages.sort()
                collection.packages.allPackages = packages
            self.all_packages.extend(packages)
        else:
            for component in self.selected_components:
                if component not in repo.components:
                    if component not in self.missing_components:
                        self.missing_components.append(component)
                    return
                for package in repo.components[component]:
                    collect(package)

            for package in self.selected_packages:
                collect(package)

            packages.sort()
            self.all_packages = packages

        self.all_packages.sort()

        # Find all root image packages
        packages = []
        self.all_root_image_packages = []

        for component in self.selected_root_image_components:
            if component not in repo.components:
                if component not in self.missing_components:
                    self.missing_components.append(component)
                return
            for package in repo.components[component]:
                collect(package)

        for package in self.selected_root_image_packages:
            collect(package)

        packages.sort()
        self.all_root_image_packages = packages
        
        # Find all desktop image packages
        
        packages = []
        self.all_desktop_image_packages = []

        for component in self.selected_desktop_image_components:
            if component not in repo.components:
                if component not in self.missing_components:
                    self.missing_components.append(component)
                return
            for package in repo.components[component]:
                collect(package)

        for package in self.selected_desktop_image_packages:
            collect(package)

        packages.sort()
        self.all_desktop_image_packages = packages
        
        # Find all livecd image packages
        
       
        packages = []
        self.all_livecd_image_packages = []

        for component in self.selected_livecd_image_components:
            if component not in repo.components:
                if component not in self.missing_components:
                    self.missing_components.append(component)
                return
            for package in repo.components[component]:
                collect(package)

        for package in self.selected_livecd_image_packages:
            collect(package)

        packages.sort()
        self.all_livecd_image_packages = packages

    def image_repo_dir(self, clean=False):
        return self._get_dir("image_repo", clean)

    def image_dir(self, clean=False):
        return self._get_dir("rootimage", clean)
    
    def desktop_image_dir(self, clean=False):
        return self._get_dir("desktopimage", clean)
    
    def initrd_image_dir(self, clean=False):
        return self._get_dir("initrdimage", clean)
    
    def livecd_image_dir(self, clean=False):
        return self._get_dir("livecdimage", clean)    

    def efi_tmp_path_dir(self, clean=False):
        return self._get_dir("efi_tmp", clean) 

    def install_repo_dir(self, clean=False):
        return self._get_dir("install_repo", clean)

    def iso_dir(self, clean=False):
        return self._get_dir("iso", clean)

    def iso_file(self, clean=True):
        filename = self.title.replace(" ", "-")
        filename = re.sub("[()]", "", filename)
        path = os.path.join(self.work_dir, "%s.iso" % filename)
        if clean and os.path.exists(path):
            os.unlink(path)
        return path
