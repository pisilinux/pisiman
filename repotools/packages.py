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

import os
import sys
import urllib2
import piksemel
import random
import string
import random

from utility import xterm_title

class Console:
    def started(self, title):
        print title

    def progress(self, msg, percent):
        sys.stdout.write("\r%-70.70s" % msg)
        sys.stdout.flush()

    def finished(self):
        sys.stdout.write("\n")


class ExPisiIndex(Exception):
    pass

class ExIndexBogus(ExPisiIndex):
    pass

class ExPackageMissing(ExPisiIndex):
    pass

class ExPackageCycle(ExPisiIndex):
    pass


def fetch_uri(base_uri, cache_dir, filename, console=None, update_repo=False):
    # Dont cache for local repos
    if base_uri.startswith("file://") and not filename.startswith("pisi-index.xml"):
        return os.path.join(base_uri[7:], filename)

    # Check that local file isnt older or has missing parts
    path = os.path.join(cache_dir, filename)
    if not os.path.exists(path) or (update_repo and filename.startswith("pisi-index.xml")):
        if console:
            console.started("Fetching '%s'..." % filename)
        try:
            connection = urllib2.urlopen(os.path.join(base_uri, filename))
        except ValueError:
            raise ExIndexBogus
        filedir = path[:path.rfind("/")]
        os.system("mkdir -p %s" % filedir)
        output = file(path, "w")
        total_size = int(connection.info()['Content-Length'])
        size = 0
        while size < total_size:
            data = connection.read(4096)
            output.write(data)
            size += len(data)
            if console:
                console.progress("Downloaded %d of %d bytes" % (size, total_size), 100 * size / total_size)
        output.close()
        connection.close()
        if console:
            console.finished()
    return path

def random_id():
     """ Create an id of random length between 8 and 16
             characters long, made up of numbers and letters.
     """
     return "".join(random.choice(string.ascii_letters + string.digits) for x in range(random.randint(8, 16)))

class PackageCollection(object):

    _id = ""

    def __init__(self, id=None, icon=None, translations={}, packages=None, default=""):
        if id:
            self._id = id
        else:
            self._id = random_id()
        self.icon = icon
        self.translations = translations
        self.packages = packages
        self.default =  default

    def __eq__(self, collection):
        return self._id == collection._id and \
               self.translations == collection.translations and \
               self.icon == collection.icon and \
               self.packages == collection.packages

    def __str__(self):
        return """"Collection:
id: %s
icon: %s
translations: %s
default: %s
""" % (self._id, self.icon, self.translations, self.default)

class PackageSet(object):
    def __init__(self, repoURI, selectedComponents=[], selectedPackages=[], allPackages=[]):
        self.repoURI = repoURI
        self.selectedComponents = selectedComponents
        self.selectedPackages = selectedPackages
        self.allPackages = allPackages

    def __eq__(self, packages):
        return self.repoURI == packages.repoURI and \
                self.selectedComponents == packages.selectedComponents and \
                self.selectedPackages == packages.selectedPackages and \
                self.allPackages == packages.allPackages

    def __str__(self):
        return """PackageSet: (%s)
selected components: %s
selected packages: %s
all packages: %s
""" % (self.repoURI, self.selectedComponents,
                        self.selectedPackages, self.allPackages)

class Package:
    def __init__(self, node):
        self.node = node
        self.name = node.getTagData('Name')
        self.icon = node.getTagData('Icon')
        if not self.icon:
            self.icon = 'package'
        self.homepage = node.getTag('Source').getTagData('Homepage')
        self.version = node.getTag('History').getTag('Update').getTagData('Version')
        self.release = node.getTag('History').getTag('Update').getAttribute('release')
        self.build = node.getTagData('Build')
        self.size = int(node.getTagData('PackageSize'))
        self.inst_size = int(node.getTagData('InstalledSize'))
        self.uri = node.getTagData('PackageURI')
        self.sha1sum = node.getTagData('PackageHash')
        self.component = node.getTagData('PartOf')
        self.summary = ""
        self.description = ""
        for tag in node.tags():
            if tag.name() == "Summary" and tag.getAttribute("xml:lang") == "en":
                self.summary = tag.firstChild().data()
        for tag in node.tags():
            if tag.name() == "Description" and tag.getAttribute("xml:lang") == "en":
                self.description = tag.firstChild().data()
        deps = node.getTag('RuntimeDependencies')
        if deps:
            self.depends = map(lambda x: x.firstChild().data(), deps.tags('Dependency'))
            for anyDeps in deps.tags("AnyDependency"):
                self.depends.append(anyDeps.getTagData("Dependency"))
        else:
            self.depends = []
        self.revdeps = []
        # Keep more info: licenses, packager name

    def __str__(self):
        return """Package: %s (%s)
                  Version %s, release %s, build %s
                  Size: %d, installed %d
                  Part of: %s
                  Dependencies: %s
                  Reverse dependencies: %s
                  Summary: %s""" % (
            self.name, self.uri,
            self.version, self.release, self.build,
            self.size, self.inst_size,
            self.component,
            ", ".join(self.depends),
            ", ".join(self.revdeps),
            self.summary
        )


class Component:
    def __init__(self, node):
        self.node = node
        self.name = node.getTagData('Name')
        self.packages = []

    def __str__(self):
        return "Component: %s\nPackages: %s" % (self.name, ", ".join(self.packages))


class Repository:
    def __init__(self, uri, cache_dir):
        self.index_name = os.path.basename(uri)
        self.base_uri = os.path.dirname(uri)
        self.cache_dir = cache_dir
        self.size = 0
        self.inst_size = 0
        self.packages = {}
        self.components = {}

    def parse_index(self, console=None, update_repo=False):
        path = fetch_uri(self.base_uri, self.cache_dir, self.index_name, console, update_repo)
        if path.endswith(".bz2"):
            import bz2
            data = open(path).read()
            data = bz2.decompress(data)
            doc = piksemel.parseString(data)
        elif path.endswith(".xz"):
            try:
                import lzma
            except ImportError:
                print "Install python-pyliblzma package, or try a different index format."
                return

            data = open(path).read()
            data = lzma.decompress(data)
            doc = piksemel.parseString(data)
        else:
            doc = piksemel.parse(path)
        for tag in doc.tags('Package'):
            p = Package(tag)
            self.packages[p.name] = p
            self.size += p.size
            self.inst_size += p.inst_size
            if p.component not in self.components:
                self.components[p.component] = []
        for name in self.packages:
            p = self.packages[name]
            for name2 in p.depends:
                if self.packages.has_key(name2):
                    self.packages[name2].revdeps.append(p.name)
                else:
                    raise ExPackageMissing, (p.name, name2)
            if p.component in self.components:
                self.components[p.component].append(p.name)
            else:
                self.components[p.component] = []
        from pisi.graph import Digraph, CycleException
        dep_graph = Digraph()
        for name in self.packages:
            p = self.packages[name]
            for dep in p.depends:
                dep_graph.add_edge(name, dep)
        try:
            dep_graph.dfs()
        except CycleException, c:
            raise ExPackageCycle, (c.cycle)

    def make_index(self, package_list):
        doc = piksemel.newDocument("PISI")

        # since new PiSi (pisi 2) needs component info in index file, we need to copy it from original index that user specified
        indexpath = fetch_uri(self.base_uri, self.cache_dir, self.index_name, None, False)
        if indexpath.endswith(".bz2"):
            import bz2
            data = open(indexpath).read()
            data = bz2.decompress(data)
            doc_index = piksemel.parseString(data)
        elif indexpath.endswith(".xz"):
            try:
                import lzma
            except ImportError:
                print "Install python-pyliblzma package, or try a different index format."
                return

            data = open(indexpath).read()
            data = lzma.decompress(data)
            doc_index = piksemel.parseString(data)
        else:
            doc_index = piksemel.parse(indexpath)

        # old PiSi needs obsoletes list, so we need to copy it too.
        for comp_node in doc_index.tags("Distribution"):
            doc.insertNode(comp_node)

        for name in package_list:
            doc.insertNode(self.packages[name].node)

        for comp_node in doc_index.tags("Component"):
            doc.insertNode(comp_node)

        return doc.toPrettyString()

    def make_local_repo(self, path, package_list, index_name="pisi"):
        index = 0
        for name in package_list:
            package = self.packages[name]
            xterm_title("Fetching : %s - %s of %s" % (name, index, len(package_list)))
            console = Console()
            cached = fetch_uri(self.base_uri, self.cache_dir, package.uri, console)
            subpath = os.path.dirname(package.uri)
            if not os.path.exists(os.path.join(path, subpath, os.path.basename(cached))):
                if not os.path.exists(os.path.join(path, subpath)):
                    os.makedirs(os.path.join(path, subpath))
                os.symlink(cached, os.path.join(path, subpath, os.path.basename(cached)))
            index += 1
        index = self.make_index(package_list)
        import bz2
        data = bz2.compress(index)
        import hashlib
        f = file(os.path.join(path, "%s-index.xml.bz2") % index_name, "w")
        f.write(data)
        f.close()
        f = file(os.path.join(path, "%s-index.xml.bz2.sha1sum") % index_name, "w")
        s = hashlib.sha1()
        s.update(data)
        f.write(s.hexdigest())
        f.close()

    def make_collection_index(self, path, projectCollections, default_language):
        doc = piksemel.newDocument("YALI")
        for collection in projectCollections:
            collectionTag = doc.insertTag("Collection")
            if collection.default:
                collectionTag.setAttribute("default", collection.default)
            collectionTag.insertTag("id").insertData(collection._id)
            collectionTag.insertTag("icon").insertData(collection.icon)
            translationsTag = collectionTag.insertTag("translations")
            translationsTag.setAttribute("default", default_language)
            for languageCode, translation in collection.translations.items():
                translationTag = translationsTag.insertTag("translation")
                translationTag.setAttribute("language", languageCode)
                translationTag.insertTag("title").insertData(translation[0])
                translationTag.insertTag("description").insertData(translation[1])

        f = file(os.path.join(path, "collection.xml"), "w")
        f.write(doc.toPrettyString())
        f.close()

        import hashlib
        f = file(os.path.join(path, "collection.xml.sha1sum"), "w")
        s = hashlib.sha1()
        s.update(doc.toPrettyString())
        f.write(s.hexdigest())
        f.close()

    def full_deps(self, package_name):
        deps = set()
        deps.add(package_name)

        def collect(name):
            p = self.packages[name]
            for item in p.depends:
                deps.add(item)
                collect(item)

        collect(package_name)

        return deps

    def __str__(self):
        return """Repository: %s
                  Number of packages: %d
                  Total package size: %d
                  Total installed size: %d""" % (
            self.base_uri,
            len(self.packages),
            self.size,
            self.inst_size
        )


