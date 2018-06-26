# Installing CentOS

BIOS GPT

## Preface
This is the first tutorial of a many part series intended to demonstrate one approach to setting up a home network. While later tutorials will include adding Windows machines to the network, as well as detailing the creation and administration of an Active Directory (AD) domain, the initial tutorials will explain the creation of a network comprised of only Linux SERVERS, although clients of any OS type can easily be added to the network.

## Hardware
I'm using a number of Virtualbox VMs as well as a wide variety of hardware in my network - ranging from an old Dell Inspiron Laptop to an assortment of Raspberry Pi's, and , so don't feel as though you need anything particular/special.

For this tutorial I'm using an Dell Inspiron N5050.
* Processor: Intel i3
* Hard Drive: 500G SSD
* RAM 4G
* Firmware: BIOS

One thing to note here is that because we lack UEFI firmware AND have a disk smaller than 2TB, the CentOS installer will, by default, create a Master Boot Record (MBR) partition table. We can, however, instruct the installer to create a GUID Partition Table (GPT), as detailed [below](#).

<!-- If you're using a Raspberry Pi, you may opt to stick with the Debian-derived Raspbian image. If this is the case, feel free to skip the remainder of this tutorial. I feel that the installation of the ARM build of Arch Linux onto a Raspberry Pi merits a full post, and as such it will be addressed in a later tutorial. With that said if you're using other hardware, or just feel like reading, let's get started. -->

## Linux Distros


## Download ISO and create bootable USB
First lets download the Centos Minimal Install ISO and the associated checksums
```bash
$ wget http://${some_mirror}/linux/centos/7/isos/x86_64/CentOS-7-x86_64-Minimal-1804.iso \
       http://${some_mirror}/linux/centos/7/isos/x86_64/sha256sum.txt
```

We'll delete all the checksums except for the one corresponding to the minimal iso, and then verify
```bash
$ sed -i '/CentOS-7-x86_64-Minimal-1804.iso/!d' sha256sum.txt
$ shasum -a 256 -c sha256sum.txt
CentOS-7-x86_64-Minimal-1804.iso: OK
```

Now check the size, find a flash drive with at least that amount of space (~1Gi), and copy the image to the USB
```bash
$ du -h CentOS-7-x86_64-Minimal-1804.iso
907M	CentOS-7-x86_64-Minimal-1804.iso
$ du status=progress if=CentOS-7-x86_64-Minimal-1804.iso of=/dev/sdX
```

## Install
With the flash drive inserted into a USB port of the machine on which you want to install Centos, reboot and hold/press F12 to bring up the boot options, selecting the one which says `USB Storage Device` - or something similar.

From there you'll be presented with an additional list of options;
1. Navigate to `Install CentOS 7`.
2. Request a GUID Partition Table (GPT)
..1. Press TAB to bring up the installer boot command line
..2. Append the option `inst.gpt`
..3. Press ENTER

Now you'll be presented with a GUI allowing you to select various configuration preferences such as language/locale, keyboard layout, timezone preferences, etc. Choose whichever is appropriate. Two important options are:
1. Network and Hostname
   Replace localhost.localdomain with a NON-fully-qualified domain name. Domain setup is part of a later tutorial - not to mention we currently lack any network connection - so just select a hostname which will correspond to your machine and which DOES NOT end in a `.`. I've selected `server1`.
2. Installation Destination
..1. Select the disk on which you want to install CentOS
..2. Select automatically configure partitioning
..3. Select Encrypt my data (to enable LUKS encryption of the root partition) and choose a passphrase

Now select `Begin Installation`

1. Root password: set a root password (Ideally a different password from that used for the LUKS partition)
2. Create a non-root user
..*Select `Make this user administrator` to add your user to the `wheel` group and give them `sudo` access


# Encrypt boot partition
Now you have a working CentOS server. After logging in, let's look at the partitioned disks(s).
```bash
# lsblk
NAME           MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINT
sda              0:0    0 465.8G  0 disk
└─sda1           8:1    0 953.2G  0 part  
└─sda2           8:1    0 953.2G  0 part  
  └─cryptmain  254:0    0 953.2G  0 crypt 
    ├─vg0-swap 254:1    0     8G  0 lvm   [SWAP]
    ├─vg0-root 254:2    0    15G  0 lvm   /
    └─vg0-home 254:3    0 930.2G  0 lvm   /home
```

Encrypting the partition is an excellent step, but only the first one. An unencrypted boot partition opens you up to an Evil Maid attack. The details of this attack are beyond the scope of this post, but essentialy because the boot partition is unencrypted, an attacker with physical access to your machine could plant a bootkit by by replacing or modifying:
1. any one of the GRUB stage 2 modules
2. the initial ramdisk (initramfs) or any of the files in it
3. the kernel itself.



cp -a /boot/. /boot-backup
umount /boot
cryptsetup luksFormat --verify-passphrase /dev/sda1
cryptsetup luksOpen /dev/sda1 luks-
mkfs -t ext4 /dev/mapper/luks-
mount -t ext4 /dev/mapper/luks- /boot
cp -a /boot-backup/. /boot/
rm -rf /boot-backup

sed -i '/UUID/d' /etc/fstab
echo 'GRUB_ENABLE_CRYPTODISK=y' >> /etc/default/grub
grub2-mkconfig -o /boot/grub2/grub.cfg
grub2-install /dev/sda

## Mounting the boot partition after the kernel starts
You may notice that after the boot sequence is complete, the boot partition (/dev/sda1) is not mounted to /boot. This is because you only gave the requisite passphrase to GRUB 1.5. The kernel, on the other hand, lacks this information; therefore, merely adding a corresponding entry to /etc/fstab would not suffice. Fortunately, in addition to interactive decryption, LUKS can decrypt devices using keyfiles, which presents a solution to this dilemma.

1. Create a keyfile
```bash
# openssl rand 2048 -out /etc/luks--key
# chmod 400 /etc/luks--key
```
2. Add the keyfile to the LUKS header on /dev/sda1
```bash
# cryptsetup luksAddKey --key-file /etc/luks--key --keyfile-size 2048 /dev/sda1
# cryptsetup -v luksOpen --key-file /etc/luks--key --test-passphrase /dev/sda1
Key slot 1 unlocked
Command successful
```

3. Update /etc/crypttab
```
# <name>       <device>                                     <password>              <options>
luks-            UUID=                                        /etc/luks--key          luks
```

4. Update /etc/fstab
```
UUID= / ext4 rw 0 2
```

# Troubleshooting

## Incorrectly entered boot partition passphrase
GRUB rescue is not particularly elaborate - which is understandable; after all it only has 32,256 bytes (i.e. the size of the post-MBR gap) in which to store its code. As such, if you incorrectly enter the passphrase for your newly created boot partition, GRUB will drop you into a rescue shell instead of reprompting you. 

Far more limited than its Stage 2 analog, the GRUB rescue shell contains only a handful of commands which, unfortunately, do not include `help` or `?`. However, the boot sequence can still be resumed with the following commands.

1. Unlock and mount the boot partition (/dev/sda1)
```bash
grub-rescue> cryptomount (hd0,msdos1)
```
2. Load the `normal` module
```bash
grub-rescue> insmod normal
```

3. Resume the boot sequence
```bash
grub-rescue> normal
```

## Other problems
Sometimes, you may encounter a problem which stops you from even reaching the GRUB rescue shell. For example, lets assume that in the boot partition encryption process, you forgot the final `grub2-install /dev/sda` command. In this case, the GRUB Stage 1.5 bootloader would lack the LUKS modules necessary to decrypt the boot partition. Since you can't boot the system into any sort of recovery shell, the solution is to boot from an external medium and correct the problem - which in this case would involve running `grub2-install /dev/sda`.

First, if you don't already have one, create a bootable USB flash drive like the one you used to install CentOS. In fact all you need is a shell; no GUI required. One the OS is up and running, you'll need to recreate the environment of your actual HOST OS before running the commands.

1. Decrypt the encrypted partitions
```bash
# cryptsetup luksOpen /dev/sda1 luks-
# cryptsetup luksOpen /dev/sda2 luks-

# mount -t xfs /dev/centos/root /mnt
# mount -t xfs /dev/centos/home /mnt/home
# mount -t ext4 /dev/luks- /boot
# swapon /dev/centos/swap

# mount -t proc /mnt/proc/
# mount --rbind /dev /mnt/dev/
# mount --rbind /sys /mnt/sys/
# mount --rbind /run /mnt/run/
# chroot /mnt /bin/bash
# grub2-install /dev/sda
```

Now reboot into your host system and everything should proceed as normally.
