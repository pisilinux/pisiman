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
import sys
import time
from repotools import packages


def maker(op, project_file):
    from repotools import maker, project

    project = project.Project()
    err = project.open(project_file)
    if err:
        print "ERROR: %s" % err
        return

    start = time.time()

    if op == "make" or op == "make-repo":
        update_repo = True
        while True:
            try:
                project.get_repo(update_repo=update_repo)
            except packages.ExIndexBogus, e:
                print "ERROR: Unable to load package index. URL is wrong, or file is corrupt."
                return
            except packages.ExPackageCycle, e:
                cycle = " > ".join(e.args[0])
                print "ERROR: package index has errors. Cyclic dependency found:\n  %s." % cycle
                return
            except packages.ExPackageMissing, e:
                print "ERROR: Package index has errors. '%s' depends on non-existing '%s'." % e.args
                return
            missing_components, missing_packages = project.get_missing()

            if len(missing_components):
                print "WARNING: There are missing components. Removing."
                print "\n".join(missing_components)
                if project.package_collections:
                    for component in missing_components:
                        for collection in project.package_collections:
                            if component in collection.packages.selectedComponents:
                                collection.packages.selectedComponents.remove(component)
                else:
                    for component in missing_components:
                        if component in project.selected_components:
                            project.selected_components.remove(component)
                update_repo = False
            if len(missing_packages):
                print "WARNING: There are missing packages. Removing."
                print "\n".join(missing_packages)
                if project.package_collections:
                    for package in missing_packages:
                        for collection in project.package_collections:
                            if package in collection.packages.selectedPackages:
                                collection.packages.selectedPackages.remove(package)
                else:
                    for package in missing_packages:
                        if package in project.selected_packages:
                            project.selected_packages.remove(package)
                update_repo = False
            break
        maker.make_repos(project)
        
    #if op == "check-repo":
        #maker.check_repo_files(project)
    if op == "make" or op == "make-live":
        maker.make_image(project)
    # install-live
    # configure-live
    if op == "make" or op == "pack-live":
        maker.squash_image(project)
    if op == "make" or op == "make-iso":
        maker.make_iso(project)

    end = time.time()
    print "Total time is", end - start, "seconds."


def usage(app):
    print "Usage: %s [command] path/to/project.xml" % app
    print
    print "Commands:"
    print "  make-repo  : Make local repos"
    print "  check-repo : Check repo files"
    print "  make-live  : Install image"
    print "  pack-live  : Make squashfs"
    print "  make-iso   : Make ISO"
    print "  make       : Make all!"


def main(args):
    if len(args) == 2 and args[1] in ["help", "-h", "--help"]:
        usage(args[0])
    elif len(args) == 3:
        maker(args[1], args[2])
    else:
        import gui
        gui.gui(args)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
