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
import stat
import time
import dbus
import glob
import shutil
import hashlib
import tempfile

from repotools.utility import xterm_title, wait_bus

#
# Utilities
#

def run(cmd, ignore_error=False):
    print cmd
    ret = os.system(cmd)
    if ret and not ignore_error:
        print "%s returned %s" % (cmd, ret)
        sys.exit(1)

def connectToDBus(path):
    global bus
    bus = None
    for i in range(20):
        try:
            print("trying to start dbus..")
            bus = dbus.bus.BusConnection(address_or_type="unix:path=%s/run/dbus/system_bus_socket" % path)
            break
        except dbus.DBusException:
            time.sleep(1)
            print("wait dbus for 1 second...")
    if bus:
        return True
    return False

def chroot_comar(image_dir):
    if os.fork() == 0:
        # Workaround for creating ISO's on 2007 with PiSi 2.*
        # Create non-existing /var/db directory before running COMAR
        try:
            os.makedirs(os.path.join(image_dir, "var/db"), 0700)
        except OSError:
            pass
        os.chroot(image_dir)
        if not os.path.exists("/var/lib/dbus/machine-id"):
            run("/usr/bin/dbus-uuidgen --ensure")

        run("/sbin/start-stop-daemon -b --start --pidfile /run/dbus/pid --exec /usr/bin/dbus-daemon -- --system")
        sys.exit(0)
    wait_bus("%s/run/dbus/system_bus_socket" % image_dir)

def get_exclude_list(project):
    exc = project.exclude_list()[:]
    image_dir = project.image_dir()
    path = image_dir + "/boot"
    for name in os.listdir(path):
        if name.startswith("initramfs"):
            exc.append("boot/" + name)
    return exc


def generate_isolinux_conf(project):
    print "Generating isolinux config files..."
    xterm_title("Generating isolinux config files")

    dict = {}
    dict["title"] = project.title
    dict["exparams"] = project.extra_params or ''

    image_dir = project.image_dir()
    iso_dir = project.iso_dir()

    lang_default = project.default_language
    lang_all = project.selected_languages


    isolinux_tmpl = """
default start    
implicit 1
ui gfxboot bootlogo 
prompt   1
timeout  200


label %(title)s
    kernel /pisi/boot/x86_64/kernel
    append initrd=/pisi/boot/x86_64/initrd.img misobasedir=pisi misolabel=pisilive overlay=free quiet %(exparams)s
    

label harddisk
    localboot 0x80

label memtest
    kernel /pisi/boot/x86_64/memtest

label hardware
    kernel hdt.c32
"""

    # write isolinux.cfg
    dest = os.path.join(iso_dir, "isolinux/isolinux.cfg")
    data = isolinux_tmpl % dict

    f = file(dest, "w")
    f.write(data % dict)
    f.close()

    # write gfxboot config for title
    data = file(os.path.join(image_dir, "usr/share/gfxtheme/pisilinux/install/gfxboot.cfg")).read()
    f = file(os.path.join(iso_dir, "isolinux/gfxboot.cfg"), "w")
    f.write(data % dict)
    f.close()

    if len(lang_all) and lang_default != "":
        langdata = ""

        if not lang_default in lang_all:
            lang_all.append(lang_default)

        lang_all.sort()

        for i in lang_all:
            langdata += "%s\n" % i


        # write default language
        f = file(os.path.join(iso_dir, "isolinux/lang"), "w")
        f.write("%s\n" % lang_default)
        f.close()

        # FIXME: this is the default language selection, make it selectable
        # when this file does not exist, isolinux pops up language menu
        if os.path.exists(os.path.join(iso_dir, "isolinux/lang")):
            os.unlink(os.path.join(iso_dir, "isolinux/lang"))

        # write available languages
        f = file(os.path.join(iso_dir, "isolinux/languages"), "w")
        f.write(langdata)
        f.close()


def setup_isolinux(project):
    print "Generating isolinux files..."
    xterm_title("Generating isolinux files")

    image_dir = project.image_dir()
    iso_dir = project.iso_dir()
    repo = project.get_repo()
    
   
    # Setup dir
    path = os.path.join(iso_dir, "isolinux")
    if not os.path.exists(path):
        os.makedirs(path)

    def copy(src, dest):
        run('cp -P "%s" "%s"' % (src, os.path.join(iso_dir, dest)))

    # Copy the kernel and initramfs
    path = os.path.join(image_dir, "boot")
    for name in os.listdir(path):
        if name.startswith("kernel") or name.startswith("initramfs") or name.endswith(".img"):
            if name.startswith("kernel"):
                copy(os.path.join(path, name), "pisi/boot/x86_64/kernel")
            elif name.startswith("initramfs"):
                copy(os.path.join(path, name), "pisi/boot/x86_64/initrd.img")

    tmplpath = os.path.join(image_dir, "usr/share/gfxtheme/pisilinux/install")
    dest = os.path.join(iso_dir, "isolinux")
    for name in os.listdir(tmplpath):
        if name != "gfxboot.cfg":
            copy(os.path.join(tmplpath, name), dest)

    # copy config and gfxboot stuff
    generate_isolinux_conf(project)

    # we don't use debug anymore for the sake of hybrid
    copy(os.path.join(image_dir, "usr/lib/syslinux/isolinux.bin"), "%s/isolinux.bin" % dest)
    copy(os.path.join(image_dir, "usr/lib/syslinux/hdt.c32"), dest)
   
    #for boot new syslinux
    copy(os.path.join(image_dir, "usr/lib/syslinux/ldlinux.c32"), dest)
    copy(os.path.join(image_dir, "usr/lib/syslinux/libcom32.c32"), dest)
    copy(os.path.join(image_dir, "usr/lib/syslinux/libutil.c32"), dest)
    copy(os.path.join(image_dir, "usr/lib/syslinux/vesamenu.c32"), dest)
    copy(os.path.join(image_dir, "usr/lib/syslinux/libmenu.c32"), dest)
    copy(os.path.join(image_dir, "usr/lib/syslinux/libgpl.c32"), dest)
    copy(os.path.join(image_dir, "usr/lib/syslinux/isohdpfx.bin"), dest)

    copy(os.path.join(image_dir, "usr/lib/syslinux/gfxboot.c32"), dest)
    copy(os.path.join(image_dir, "usr/share/misc/pci.ids"), dest)

    kernel_version = open(os.path.join(image_dir, "etc/kernel/kernel")).read()
    #copy(os.path.join(image_dir, "lib/modules/%s/modules.pcimap" % kernel_version), dest)
    copy(os.path.join(image_dir, "boot/memtest"), os.path.join(iso_dir, "pisi/boot/x86_64"))

    
#
# Image related stuff
#


def setup_live_sddm(project):
    desktop_image_dir = project.desktop_image_dir()
    
    sddmconf_path = os.path.join(desktop_image_dir, "etc/sddm.conf")
    if os.path.exists(sddmconf_path):
        lines = []
        for line in open(sddmconf_path, "r").readlines():
            if line.startswith("User"):
                lines.append("User=pisilive\n")
            elif line.startswith("Session"):
                lines.append("Session=plasma.desktop\n") #this code may be have an error
            else:
                lines.append(line)
        open(sddmconf_path, "w").write("".join(lines))
    else:
        print "*** %s doesn't exist, setup_live_sddm() returned" % sddmconf_path

def setup_live_lxdm(project):
    desktop_image_dir = project.desktop_image_dir()
    
    lxdm_path = os.path.join(desktop_image_dir, "etc/lxdm/lxdm.conf")
    if os.path.exists(lxdm_path):
        lines = []
        for line in open(lxdm_path, "r").readlines():
            if line.startswith("# autologin=dgod"):
                lines.append("autologin=live\n")
            elif line.startswith("# session=/usr/bin/startlxde"):
                lines.append("session=/usr/bin/startxfce4\n")    
            else:
                lines.append(line)
        open(lxdm_path, "w").write("".join(lines))
    else:
        print "*** %s doesn't exist, setup_live_lxdm() returned" % lxdm_path

def setup_live_mdm(project):
    desktop_image_dir = project.desktop_image_dir()

    mdm_path = os.path.join(desktop_image_dir, "usr/share/mdm/distro.conf")
    if os.path.exists(mdm_path):
        lines = []
        for line in open(mdm_path, "r").readlines():
            if line.startswith("AutomaticLoginEnable=false"):
                lines.append("AutomaticLoginEnable=true\n")
            elif line.startswith("AutomaticLogin="):
                lines.append("AutomaticLogin=Pisilive\n")
            elif line.startswith("#DefaultSession=default.desktop"):
                lines.append("DefaultSession=xfce.desktop\n")    
            else:
                lines.append(line)
        open(mdm_path, "w").write("".join(lines))
    else:
        print "*** %s doesn't exist, setup_live_mdm() returned" % mdm_path



def squash_image(project):
    image_dir = project.image_dir()
    desktop_image_dir = project.desktop_image_dir()
    livecd_image_dir = project.livecd_image_dir()
    
    sqfs_path = os.path.join(project.work_dir)
    
    print "squashfs image dir%s" % image_dir
    if not image_dir.endswith("/"):
        image_dir += "/"
    print "later squashfs image dir%s" % image_dir
    temp = tempfile.NamedTemporaryFile()
    f = file(temp.name, "w")
    f.write("\n".join(get_exclude_list(project)))
    f.close()

    mksquashfs_cmd = 'mksquashfs "%s" "%s/rootfs.sqfs" -noappend -comp %s -ef "%s"' % (image_dir, sqfs_path, project.squashfs_comp_type, temp.name)
    
    run(mksquashfs_cmd)
    
    print "squashfs image dir%s" % desktop_image_dir
    if not desktop_image_dir.endswith("/"):
        desktop_image_dir += "/"
    print "later squashfs image dir%s" % desktop_image_dir
    temp = tempfile.NamedTemporaryFile()
    f = file(temp.name, "w")
    f.write("\n".join(get_exclude_list(project)))
    f.close()

    
    
    mksquashfs_cmd1 = 'mksquashfs "%s" "%s/desktop.sqfs" -noappend -comp %s -ef "%s"' % (desktop_image_dir, sqfs_path, project.squashfs_comp_type, temp.name)
    
    run(mksquashfs_cmd1)
    
    print "squashfs image dir%s" % livecd_image_dir
    if not livecd_image_dir.endswith("/"):
        livecd_image_dir += "/"
    print "later squashfs image dir%s" % livecd_image_dir
    temp = tempfile.NamedTemporaryFile()
    f = file(temp.name, "w")
    f.write("\n".join(get_exclude_list(project)))
    f.close()

    
    
    mksquashfs_cmd2 = 'mksquashfs "%s" "%s/livecd.sqfs" -noappend -comp %s -ef "%s"' % (livecd_image_dir, sqfs_path, project.squashfs_comp_type, temp.name)
    
    run(mksquashfs_cmd2)    

#
# Operations
#

def make_repos(project):
    print "Preparing image repo..."
    xterm_title("Preparing repo")
    

    try:
        repo = project.get_repo()
        repo_dir = project.image_repo_dir(clean=True)

        imagedeps = project.all_packages
        repo.make_local_repo(repo_dir, imagedeps)

    except KeyboardInterrupt:
        print "Keyboard Interrupt: make_repo() cancelled."
        sys.exit(1)


def check_file(repo_dir, name, _hash):
    path = os.path.join(repo_dir, name)
    if not os.path.exists(path):
        print "\nPackage missing: %s" % path
        return
    data = file(path).read()
    cur_hash = hashlib.sha1(data).hexdigest()
    if cur_hash != _hash:
        print "\nWrong hash: %s" % path

def add_repo(project):    
    image_dir = project.image_dir()

    run('/bin/mount --bind /proc %s/proc' % image_dir)
    run('/bin/mount --bind /sys %s/sys' % image_dir)
    run('/bin/mount --bind /dev %s/dev' %image_dir)
    
    run("chroot \"%s\" /bin/service dbus start" % image_dir)
    
    run("chroot \"%s\" /usr/bin/pisi rr pisilinux-install" % image_dir)

    
    run("cp -p /etc/localtime %s/etc/." % image_dir,ignore_error=True)
    run("cp -p /etc/resolv.conf %s/etc/." % image_dir,ignore_error=True)

    
    configdir =os.path.join(project.config_files)
    
    
    address = open(os.path.join(configdir, "repo.conf")).read()

    run("chroot \"%s\" /usr/bin/pisi ar pisi --yes-all  --ignore-check  \"%s\"" % (image_dir,address))
    #run("chroot \"%s\" /usr/bin/pisi ar contrib --yes-all  --ignore-check  https://github.com/pisilinux/contrib/raw/master/pisi-index.xml.xz" % image_dir)
    #run("chroot \"%s\" /usr/bin/pisi ar pisilife2 --yes-all  --ignore-check  https://github.com/pisilinux/pisilife-2/raw/master/pisi-index.xml.xz" % image_dir)
    
    
    
    run("chroot \"%s\" /bin/service dbus stop" % image_dir)
    
    run('umount %s/proc' % image_dir)
    run('umount %s/sys' % image_dir)
    run('umount %s/dev' % image_dir)
    
    run("rm -rf %s/run/dbus/*" % image_dir)
    run("rm -rf %s/etc/localtime" % image_dir)
    run("rm -rf %s/etc/resolv.conf" % image_dir)
    

def make_image(project):
    global bus

    print "Preparing install image..."
    xterm_title("Preparing install image")

    try:
        repo = project.get_repo()
        repo_dir = project.image_repo_dir()
        reposs = os.path.join(project.work_dir, "repo_cache")

        image_dir = project.image_dir()
        desktop_image_dir = project.desktop_image_dir()
        initrd_image_dir = project.initrd_image_dir()
        livecd_image_dir = project.livecd_image_dir()
        efi_tmp = project.efi_tmp_path_dir()
        

       
        #umount all mount dirs
        
        run('umount %s/proc' % image_dir, ignore_error=True)
        run('umount %s/sys' % image_dir, ignore_error=True)
        run('umount -R %s' % image_dir, ignore_error=True)

        run('umount %s/proc' % desktop_image_dir, ignore_error=True)
        run('umount %s/sys' % desktop_image_dir, ignore_error=True)
        run('umount -R %s' % desktop_image_dir, ignore_error=True)

        
        run('umount %s/proc' % livecd_image_dir, ignore_error=True)
        run('umount %s/sys' % livecd_image_dir, ignore_error=True)
        run('umount -R %s' % livecd_image_dir, ignore_error=True)
        
        run('umount %s/proc' % initrd_image_dir, ignore_error=True)
        run('umount %s/sys' % initrd_image_dir, ignore_error=True)
        run('umount -R %s' % initrd_image_dir, ignore_error=True)
        
        run("umount %s"% efi_tmp,ignore_error=True)
        run("umount -l %s"% efi_tmp,ignore_error=True)

        image_dir = project.image_dir(clean=True)
        
        
        run('pisi --yes-all -D"%s" ar pisilinux-install %s --ignore-check' % (image_dir, repo_dir + "/pisi-index.xml.bz2"))
        print "project type = ",project.type
        

        root_image_packages = " ".join(project.all_root_image_packages)

        run('pisi --yes-all --ignore-comar --ignore-dep --ignore-check --ignore-package-conflicts --ignore-file-conflicts -D"%s" it %s' % (image_dir, root_image_packages))
        
        

        def chrun(cmd):
            run('chroot "%s" %s' % (image_dir, cmd))


        os.mknod("%s/dev/null" % image_dir, 0666 | stat.S_IFCHR, os.makedev(1, 3))
        os.mknod("%s/dev/console" % image_dir, 0666 | stat.S_IFCHR, os.makedev(5, 1))
        os.mknod("%s/dev/random" % image_dir, 0666 | stat.S_IFCHR, os.makedev(1, 8))
        os.mknod("%s/dev/urandom" % image_dir, 0666 | stat.S_IFCHR, os.makedev(1, 9))
        
        path = "%s/usr/share/baselayout/" % image_dir
        path2 = "%s/etc" % image_dir
        for name in os.listdir(path):
            run('cp -p "%s" "%s"' % (os.path.join(path, name), os.path.join(path2, name)))

        run('/bin/mount --bind /proc %s/proc' % image_dir)
        run('/bin/mount --bind /sys %s/sys' % image_dir)

        chrun("/sbin/ldconfig")
        chrun("/sbin/update-environment")
           
        chroot_comar(image_dir)
        chrun("/usr/bin/pisi configure-pending baselayout")

        chrun("/usr/bin/pisi configure-pending")



        connectToDBus(image_dir)

        obj = bus.get_object("tr.org.pardus.comar", "/package/baselayout")

        obj.setUser(0, "", "", "", "live", "", dbus_interface="tr.org.pardus.comar.User.Manager")

        obj.addUser(1000, "pisilive", "livecd", "/home/pisilive", "/bin/bash", "live", ["wheel", "users", "lp", "lpadmin", "cdrom", "floppy", "disk", "audio", "video", "power", "dialout"], [], [], 
            
        dbus_interface="tr.org.pardus.comar.User.Manager")
       

        # Make sure environment is updated regardless of the booting system, by setting comparison
        # files' atime and mtime to UNIX time 1

        os.utime(os.path.join(image_dir, "etc/profile.env"), (1, 1))

        #chrun('killall comar')
        run('umount %s/proc' % image_dir)
        run('umount %s/sys' % image_dir)
        
        chrun("rm -rf /run/dbus/*")
        
        #setup liveuser
               
        chrun("rm -rf /etc/sudoers")

        path1 = os.path.join(image_dir, "etc/sudoers.orig")
        path2 = os.path.join(image_dir, "etc/sudoers")
        
        run('cp "%s" "%s"' % (path1, path2))
        
        run("/bin/echo 'pisilive ALL=(ALL) NOPASSWD: ALL' >> %s/etc/sudoers" % image_dir)
        
        run("/bin/chmod 440 %s/etc/sudoers" % image_dir)
        
        install_desktop(project)
        install_livecd_util(project)
        make_initrd(project)
        add_repo(project)
        
    except KeyboardInterrupt:
        print "Keyboard Interrupt: make_image() cancelled."
        sys.exit(1)        
        
def install_desktop(project):
    print "Preparing desktop image..."
    xterm_title("Preparing desktop image")
    
    image_dir = project.image_dir()
    configdir =os.path.join(project.config_files)
    
   
    desktop_image_dir = project.desktop_image_dir(clean=True)
    
    run('mount -t aufs -o br=%s:%s=ro none %s' % (desktop_image_dir,image_dir, desktop_image_dir))
    
    desktop_image_packages = " ".join(project.all_desktop_image_packages)
            
    run('pisi --yes-all --ignore-comar --ignore-dep --ignore-check -D"%s" it %s' % (desktop_image_dir, desktop_image_packages))
    
    run('/bin/mount --bind /proc %s/proc' % desktop_image_dir)
    run('/bin/mount --bind /sys %s/sys' % desktop_image_dir)
    
    run("chroot \"%s\" /bin/service dbus start" % desktop_image_dir)

    run("chroot \"%s\" /usr/bin/pisi cp" % desktop_image_dir)
       
       
       #KDE KURULAN AYAR
    
    run("cp -rf %s/default-settings/etc/* %s/etc/" % (configdir,desktop_image_dir))
    run("cp -rf %s/default-settings/autostart %s/etc/skel/.config/" % (configdir,desktop_image_dir))
    


    run("chroot \"%s\" /bin/service dbus stop" % desktop_image_dir)
    
    run('umount %s/proc' % desktop_image_dir)
    run('umount %s/sys' % desktop_image_dir)


    run('/bin/umount -R %s' % desktop_image_dir)
    run("rm -rf %s/run/dbus/*" % desktop_image_dir)
    run("rm -rf %s/var/cache/pisi/*" % desktop_image_dir)
    

   
    setup_live_sddm(project)
    
    
def install_livecd_util(project):
    
    livecd_image_dir = project.livecd_image_dir(clean=True)
    desktop_image_dir = project.desktop_image_dir()

    image_dir = project.image_dir()
    configdir =os.path.join(project.config_files)

   
    run('mount -t aufs -o br=%s:%s=ro none %s' % (livecd_image_dir,desktop_image_dir, livecd_image_dir))
    
    run('mount -t aufs -o remount,append:%s=ro none %s' % (image_dir, livecd_image_dir))
   
    
    livecd_image_packages = " ".join(project.all_livecd_image_packages)
            
    run('pisi --yes-all --ignore-comar --ignore-dep --ignore-check -D"%s" it %s' % (livecd_image_dir, livecd_image_packages))
    
    run('/bin/mount --bind /proc %s/proc' % livecd_image_dir)
    run('/bin/mount --bind /sys %s/sys' % livecd_image_dir)
    
   
   
   #calamares modules
    
    path = os.path.join(livecd_image_dir, "etc/calamares/modules")
    if not os.path.exists(path):
        os.makedirs(path)
    
    run("cp -p %s/calamares/modules/* %s/etc/calamares/modules/" % (configdir,livecd_image_dir),ignore_error=True)
    run("cp -p %s/calamares/* %s/etc/calamares/" % (configdir,livecd_image_dir),ignore_error=True)
    
    run("cp -p %s/live/sudoers/* %s/etc/sudoers.d/" % (configdir,livecd_image_dir),ignore_error=True)

    
    
    #PisiLive Config and chmod
    
    path = os.path.join(livecd_image_dir, "home/pisilive/.config")
    if not os.path.exists(path):
        os.makedirs(path)
        
    #KDE LİVE AYAR
    
    run("cp -p %s/live/kde/.config/* %s/home/pisilive/.config/" % (configdir,livecd_image_dir),ignore_error=True)
    run("cp -rf %s/live/kde/autostart %s/home/pisilive/.config/" % (configdir,livecd_image_dir),ignore_error=True)
    os.system('/bin/chown 1000:wheel "%s/home/pisilive/.config"' % livecd_image_dir)
    os.chmod(path, 0777)
    
    run("chroot \"%s\" /bin/service dbus start" % livecd_image_dir)
    run("chroot \"%s\" /usr/bin/pisi cp" % livecd_image_dir)
    
    
    run("chroot \"%s\" /bin/service dbus stop" % livecd_image_dir)

  
    run('umount %s/proc' % livecd_image_dir)
    run('umount %s/sys' % livecd_image_dir)


    run('/bin/umount -R %s' % livecd_image_dir)
    
    run("rm -rf %s/run/dbus/*" % livecd_image_dir)
    run("rm -rf %s/var/cache/pisi/*" % livecd_image_dir)


def make_initrd(project):
    
    image_dir = project.image_dir()
   
    initrd_image_dir = project.initrd_image_dir(clean=True)
    desktop_image_dir = project.desktop_image_dir()
    
    configdir =os.path.join(project.config_files)
    
    
    run('mount -t aufs -o br=%s:%s=ro none %s' % (initrd_image_dir,image_dir,initrd_image_dir))
    
    run('mount -t aufs -o remount,append:%s=ro none %s' % (desktop_image_dir, initrd_image_dir))
    
    path = "%s/initcpio/install/" % configdir
    path2 = "%s/usr/lib/initcpio/install/" %initrd_image_dir
    for name in os.listdir(path):
        run('cp -p "%s" "%s"' % (os.path.join(path, name), os.path.join(path2, name)))    
    
    path = "%s/initcpio/hooks/" % configdir
    path2 = "%s/usr/lib/initcpio/hooks/" %initrd_image_dir
    for name in os.listdir(path):
        run('cp -p "%s" "%s"' % (os.path.join(path, name), os.path.join(path2, name)))    
    

    run("cp -p %s/mkinitcpio-live.conf %s/etc/mkinitcpio-live.conf" % (configdir,initrd_image_dir))

    run('/bin/mount --bind /proc %s/proc' %initrd_image_dir)
    run('/bin/mount --bind /sys %s/sys' %initrd_image_dir)
    run('/bin/mount -o bind /dev %s/dev' %initrd_image_dir)

    kernel_version = open(os.path.join(image_dir, "etc/kernel/kernel")).read()
    run("chroot \"%s\" /usr/bin/mkinitcpio -k %s -c '/etc/mkinitcpio-live.conf' -g /boot/initramfs" % (initrd_image_dir,kernel_version))

    run('/bin/umount %s/proc' % initrd_image_dir)
    run('/bin/umount %s/sys' % initrd_image_dir)
    run('/bin/umount %s/dev' % initrd_image_dir)
    run('/bin/umount -R %s' % initrd_image_dir)

    run("cp -p %s/boot/initramfs %s/boot/." % (initrd_image_dir,image_dir))    
    

def generate_sort_list(iso_dir):
    # Sorts the packages in repo_dir according to their size
    # mkisofs sort_file format:
    # filename   weight
    # where filename is the whole name of a file/directory and the weight is a whole
    # number between +/- 2147483647. Files will be sorted with the highest weights first
    # and lowest last. The CDs are written from the middle outwards.
    # High weighted files will be nearer to the inside of the CD.
    # Highest weight -> nearer to the inside,
    # lowest weight -> outwards
    packages = glob.glob("%s/repo/*.pisi" % iso_dir)
    package_list = dict([(k, os.stat(k).st_size) for k in packages]).items()
    package_list.sort(key=lambda x: x[1], reverse=True)

    for i in xrange(len(packages)):
        package_list.insert(i, (package_list.pop(i)[0], 100+10*i))

    # Move baselayout to the top
    for p in package_list:
        if "baselayout" in p[0]:
            package_list.insert(0, package_list.pop(package_list.index(p)))

    return package_list

def make_EFI(project):
    
    work_dir = os.path.join(project.work_dir)
    img_dir = os.path.join(project.work_dir)
    configdir =os.path.join(project.config_files)
    iso_dir = project.iso_dir()
    efi_tmp = project.efi_tmp_path_dir(clean=True)
    image_dir = project.image_dir()
    

    efi_path = os.path.join(iso_dir, "EFI")

    if not os.path.exists(efi_path):
        os.makedirs(efi_path) 
        os.makedirs(os.path.join(efi_path, "boot"))

    
    run("rm -rf %s/pisi.img" % work_dir)

    
     
    run("cp -rf %s/efi/preloader/* %s/boot/" % (configdir, efi_path))
    run("cp -rf %s/autorun/* %s/." % (configdir, iso_dir))
    
    run("cp -rf %s/boot/kernel* %s/EFI/boot/kernel.efi" % (image_dir,iso_dir))  
    run("cp -rf %s/boot/initramfs* %s/EFI/boot/initrd.img" % (image_dir,iso_dir))
    
    
    run("dd if=/dev/zero bs=1M count=40 of=%s/pisi.img"% work_dir)
    run("mkfs.vfat -n PisiLinux %s/pisi.img"% work_dir)
    run("mount %s/pisi.img %s"% (work_dir,efi_tmp))
    
    
    os.makedirs(os.path.join(efi_tmp, "EFI/boot"))

    run("cp -r %s/EFI/boot/* %s/EFI/boot/" % (iso_dir, efi_tmp),ignore_error=True)
    
    run("umount %s"% efi_tmp,ignore_error=True)
    run("umount -l %s"% efi_tmp,ignore_error=True)
    

    

    
        
        
def make_iso(project):
    print "Preparing ISO..."
    xterm_title("Preparing ISO")


    try:
        iso_dir = project.iso_dir(clean=True)
        iso_file = project.iso_file(clean=True)
        work_dir = os.path.join(project.work_dir)
        configdir =os.path.join(project.config_files)
        efi_tmp = project.efi_tmp_path_dir(clean=True)

            
        image_path = os.path.join(iso_dir, "pisi")

        if not os.path.exists(image_path):
            os.makedirs(image_path) 
            
            os.makedirs(os.path.join(image_path, "boot/x86_64"))
            os.makedirs(os.path.join(image_path, "x86_64"))

        

        make_EFI(project)
        run("cp -p %s/isomounts %s/." % (configdir, image_path))
        run("cp -p %s/*sqfs %s/x86_64/." % (work_dir, image_path))
        run("cp -p %s/pisi.img %s/EFI/." % (work_dir, iso_dir))

   
        run("touch %s/.miso" % iso_dir)

        def copy(src, dest):
            dest = os.path.join(iso_dir, dest)

            if os.path.isdir(src):
                shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".svn"))
            else:
                shutil.copy2(src, dest)

        setup_isolinux(project)


        publisher="Pisi GNU/Linux http://www.pisilinux.org"
        application="Pisi GNU/Linux Live Media"
        label="pisiLive"

        
       
        cmd ='xorriso -as mkisofs -quiet -iso-level 3 -rock -joliet -max-iso9660-filenames -omit-period -omit-version-number \
            -relaxed-filenames -allow-lowercase -volid "%s" -publisher "%s" -appid "%s" \
            -preparer "prepared by pisiman" -eltorito-boot isolinux/isolinux.bin \
            -eltorito-catalog isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table \
            -isohybrid-mbr "%s/isolinux/isohdpfx.bin" -eltorito-alt-boot -e /EFI/pisi.img -isohybrid-gpt-basdat -no-emul-boot \
            -output "%s" "%s/iso/"'% (label, publisher ,application, iso_dir, iso_file, work_dir)
       
       
        run(cmd)


    except KeyboardInterrupt:
        print "Keyboard Interrupt: make_iso() cancelled."
        sys.exit(1)

