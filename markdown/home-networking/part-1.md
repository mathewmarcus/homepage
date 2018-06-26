# Server Installation and Initial Setup

This tutorial presents the steps for setting up a base installation for any one of the servers on the network. We'll also be taking some additional steps to further harden the physical security. If you already have an image which you'd like to use you can absolutely skip this tutorial, however you may want to skim it to get an idea how your image may differ.

## Linux Distro
Centos 7

## Hardware
For this tutorial I'm using a Dell Inspiron N5050.
* Processor: Intel i3
* Hard Drive: 500G SSD
* RAM 4G
* Firmware: BIOS

One thing to note here is that because we lack UEFI firmware AND have a disk smaller than 2TB, the CentOS installer will, by default, create a Master Boot Record (MBR) partition table. We can, however, instruct the installer to create a GUID Partition Table (GPT), as detailed [below](#).


## Base Installation
### Download ISO and create bootable USB
1. Download the Centos Minimal Install ISO and the associated checksums
```bash
$ wget http://${some_mirror}/linux/centos/7/isos/x86_64/CentOS-7-x86_64-Minimal-1804.iso \
       http://${some_mirror}/linux/centos/7/isos/x86_64/sha256sum.txt
```

2. Delete all the checksums except for the one corresponding to the minimal iso, and then verify
```bash
$ sed -i '/CentOS-7-x86_64-Minimal-1804.iso/!d' sha256sum.txt
$ shasum -a 256 -c sha256sum.txt
CentOS-7-x86_64-Minimal-1804.iso: OK
```

3. Check the size, find a flash drive with at least that amount of space (~1Gi), and copy the image to the USB
```bash
$ du -h CentOS-7-x86_64-Minimal-1804.iso
907M	CentOS-7-x86_64-Minimal-1804.iso
$ du status=progress if=CentOS-7-x86_64-Minimal-1804.iso of=/dev/sdX
```

### Install
With the flash drive inserted into a USB port of the machine on which you want to install Centos, reboot and hold/press F12 to bring up the boot options, selecting the one which says `USB Storage Device` - or something similar.

From there you'll be presented with an additional list of options;
1. Navigate to `Install CentOS 7`.
2. Request a GUID Partition Table (GPT)
  1. Press TAB to bring up the installer boot command line
  2. Append the option `inst.gpt`
  3. Press ENTER

Now you'll be presented with a GUI allowing you to select various configuration preferences such as language/locale, keyboard layout, timezone preferences, etc. While making your selections, take note of two important options:
1. Network and Hostname
   Replace localhost.localdomain with a NON-fully-qualified domain name. Domain setup is part of a later tutorial - and currently we're not assuming any network connectivity - so just select a hostname which will correspond to your machine and which DOES NOT end in a `.`. I've selected `server`.
2. Installation Destination
..1. Select the disk on which you want to install CentOS
..2. Select `automatically configure partitioning`
..3. Select `Encrypt my data` (to enable LUKS encryption of the root partition) and choose a passphrase

Now select `Begin Installation`, and while the install proceeds you will be presented with two final options

1. Root password: set a root password (Ideally a different password from that used for the LUKS partition)
2. Create a non-root user
..* Enter a third distinct password
..* Select `Make this user administrator` to add your user to the `wheel` group and give them `sudo` access

The install process will take some time to finish. After it's complete, press `Reboot` to boot your new system.


## Additional Configuration
### Inspecting the new system partitions
On bootup, the GRUB Stage 2 bootloader will prompt you for the passphrase you entered for the encyrpted root partition. Enter it, and then you will be prompted with the familiar tty login. For now, since almost all of the following tasks will require root access, login as the root user (we'll disable this later).

After logging in let's examine the the partitioned disks(s).
```bash
$ lsblk -o name,type,size,uuid,fstype,mountpoint
NAME                                          TYPE    SIZE UUID                                   FSTYPE      MOUNTPOINT
sda                                           disk  465.8G                                                    
├─sda1                                        part      1M                                                    
├─sda2                                        part      1G 550016b9-f79c-4176-be50-e753166fc589   xfs         /boot
└─sda3                                        part  464.8G 4809d477-1190-4ac3-aa4a-abf69d961578   crypto_LUKS 
  └─luks-4809d477-1190-4ac3-aa4a-abf69d961578 crypt 464.8G 6FBOVP-dDke-PZif-UpAZ-Fnnu-Ug2r-ZBSeJ4 LVM2_member 
    ├─centos_server-root                      lvm      50G d7718a14-a0d6-4401-8918-8eb0a862869f   xfs         /
    ├─centos_server-swap                      lvm     3.9G b4867c19-5744-48b8-b65f-34dc3c51b52b   swap        [SWAP]
    └─centos_server-home                      lvm   410.9G 204b1e48-4035-4ea5-be30-d1b7849f0f21   xfs         /home
```

We've modified the default `lsblk` output slightly to include pertinent information. For here we can see our primary disk (sda) and all of it's partitions. Let's analyze them in order.

#### sda1
This partition is a mere 1M in size, has no filesystem - hence the lack of a filesystem UUID in the UUID column, and is thus unmounted. Nevertheless, it plays a very important role: it's the BIOS boot partition. In order to explain it's purpose, we need a little background.

GRUB Stage 1 occupies the first 446 bytes of the first 512 byte sector (sector 0) of a disk (the remaining bytes of the first section contain the MBR partition table). Due to this hard 446 byte limit, GRUB Stage 1 is little more than a pointer to GRUB Stage 1.5 which, in MBR partitioned disks, occupies the 63 sectors (32256 bytes) before the first partition entry, a region known as the post-MBR gap. 

This post-MBR gap solution does not, however, work for GPT partitioned disks because this area is used to store the GPT partition table. So in this case (i.e. in our case), the GRUB Stage 1.5 bootloader is placed into a specially labeled partition; for us, this is sda1.

We can verify the existence of this label with `parted`
```bash
$ parted /dev/sda unit Mi print
Model: ATA ST500LM012 HN-M5 (scsi)
Disk /dev/sda: 476940MiB
Sector size (logical/physical): 512B/512B
Partition Table: gpt
Disk Flags: pmbr_boot

Number  Start    End        Size       File system  Name  Flags
 1      1.00MiB  2.00MiB    1.00MiB                       bios_grub
 2      2.00MiB  1026MiB    1024MiB    xfs
 3      1026MiB  476940MiB  475914MiB
```

`parted` represents this label as `bios_grub`.

#### sda2
This 1G partition has an XFS filesystem mounted to /boot and contains GRUB Stage 2, i.e. all of the configuration files and additional modules necessary to start the kernel.

It is identified in /etc/fstab by its filesystem UUID, which, according to the above `parted` output is 550016b9-f79c-4176-be50-e753166fc58.
```bash
$ grep 550016b9-f79c-4176-be50-e753166fc58 /etc/fstab
UUID=550016b9-f79c-4176-be50-e753166fc589 /boot                   xfs     defaults        0 0
```

#### sda3
This is our LUKS encrypted root partition, which we can verify using `cryptsetup` (or by examing the FSTYPE column of the above `lsblk` output):
```bash
$ cryptsetup -v isLuks /dev/sda3
Command Successful
```

After Grub Stage 2 has loaded the kernel and the initramfs into memory and started the kernel, the kernel promps us for a passphrase and opens (i.e. decrypts and then mounts) this partition using modules in initramfs, which at that point is mounted to / as the root filesystem.

##### luks-4809d477-1190-4ac3-aa4a-abf69d961578
This is our decrypted LUKS partition. By again examining the above `lsblk` output, we can see that the UUID in the name corresponds to the filesystem ID sda3 LUKS partition.

This FSTYPE column of the `lsblk` output contains LVM2_member, revealing that this a Logical Volume Manager (LVM) physical volume (PV).

Let's get some more information about this volume
```bash
$ pvdisplay /dev/mapper/luks-4809d477-1190-4ac3-aa4a-abf69d961578
  --- Physical volume ---
  PV Name               /dev/mapper/luks-4809d477-1190-4ac3-aa4a-abf69d961578
  VG Name               centos_server
  PV Size               <464.76 GiB / not usable 4.00 MiB
  Allocatable           yes 
  PE Size               4.00 MiB
  Total PE              118977
  Free PE               1
  Allocated PE          118976
  PV UUID               6FBOVP-dDke-PZif-UpAZ-Fnnu-Ug2r-ZBSeJ4
```
From this we can see that the luks-4809d477-1190-4ac3-aa4a-abf69d961578 PV belongs to the volume group (VG) centos_server.

Inspection of the centos_server VG reveals that luks-4809d477-1190-4ac3-aa4a-abf69d961578 is the sole member, contributing all of the 464.75 Gi of space

```bash
$ vgdisplay centos_server
  --- Volume group ---
  VG Name               centos_server
  System ID             
  Format                lvm2
  Metadata Areas        1
  Metadata Sequence No  4
  VG Access             read/write
  VG Status             resizable
  MAX LV                0
  Cur LV                3
  Open LV               3
  Max PV                0
  Cur PV                1
  Act PV                1
  VG Size               464.75 GiB
  PE Size               4.00 MiB
  Total PE              118977
  Alloc PE / Size       118976 / 464.75 GiB
  Free  PE / Size       1 / 4.00 MiB
  VG UUID               uFlK14-C8N5-WcOZ-s8oB-vrLq-0hSj-n2rJ7o
```

Lets run one final command to identify the logical volumes contained within the centos_server VG
```bash
$ lvdisplay centos_server
  --- Logical volume ---
  LV Path                /dev/centos_server/swap
  LV Name                swap
  VG Name                centos_server
  LV UUID                nfdI6F-nZpm-Opkn-2vqr-aonQ-1lrG-mq7vtm
  LV Write Access        read/write
  LV Creation host, time server, 2018-06-25 23:48:34 -0400
  LV Status              available
  # open                 2
  LV Size                <3.88 GiB
  Current LE             992
  Segments               1
  Allocation             inherit
  Read ahead sectors     auto
  - currently set to     256
  Block device           253:2
   
  --- Logical volume ---
  LV Path                /dev/centos_server/home
  LV Name                home
  VG Name                centos_server
  LV UUID                IGk2gR-y5mz-1AEr-cM9f-O6HV-nhNY-mmUfvs
  LV Write Access        read/write
  LV Creation host, time server, 2018-06-25 23:48:34 -0400
  LV Status              available
  # open                 1
  LV Size                <410.88 GiB
  Current LE             105184
  Segments               1
  Allocation             inherit
  Read ahead sectors     auto
  - currently set to     256
  Block device           253:3
   
  --- Logical volume ---
  LV Path                /dev/centos_server/root
  LV Name                root
  VG Name                centos_server
  LV UUID                wIeMkS-x5eK-klnv-PCxr-FNYB-5plj-6azIoV
  LV Write Access        read/write
  LV Creation host, time server, 2018-06-25 23:48:39 -0400
  LV Status              available
  # open                 1
  LV Size                50.00 GiB
  Current LE             12800
  Segments               1
  Allocation             inherit
  Read ahead sectors     auto
  - currently set to     256
  Block device           253:1
```
And sure enough, we see the three final partitions from the above `lsblk` output in the form of logical volumes (LV)s

1. 50.00 Gi LV with an XFS filesystem mounted to /root
  * /etc/fstab entry: /dev/mapper/centos_server-root / xfs defaults,x-systemd.device-timeout=0 0 0
2. 3.88 Gi LV functioning as swap space
  * /etc/fstab entry: /dev/mapper/centos_server-swap swap swap defaults,x-systemd.device-timeout=0 0 0
3. ~410.8 (i.e. the remaining disk space) Gi LV with an XFS filesystem mounted to /home
  * /etc/fstab entry: /dev/mapper/centos_server-home /home xfs defaults,x-systemd.device-timeout=0 0 0

#### Why LVM?
This use of LVM is ideal for our use case, because when we later want to install and run an NFS or Samba file server we can easily add physical volumes to the centos_server volume group and then extended one of the logical volumes if we ever find ourselves running low on space. We will never need to modify the underlying partitions.


### Encrypt boot partition
Encrypting the root partition is an excellent step, but only the first one. An unencrypted boot partition opens you up to an Evil Maid attack. The details of this attack are beyond the scope of this post, but essentialy because the boot partition is unencrypted an attacker with physical access to your machine could, with relative ease, install a bootkit by replacing or modifying:
1. any one of the GRUB stage 2 modules
2. the initial ramdisk (initramfs) or any of the files in it
3. the kernel itself.

By encrypting the boot partition, we can attempt to stave off - or at the very least hinder - these types of attacks.

1. Backup all the data on your existing boot partition and verify that the contexts are identical
```bash
mkdir /boot-backup
cp -a /boot/. /boot-backup
diff -r /boot /boot-backup
```

2. Unmount the existing boot partition
```bash
umount /boot
```

3. Create the new LUKS partition on /dev/sda2 (i.e. the current boot partition) ***This will overwrite filesystem info on the existing boot partition***
```bash
cryptsetup luksFormat --verify-passphrase /dev/sda2
```

4. Decrypt and mount the partition.
```bash
cryptsetup luksOpen /dev/sda2 luks-fa634f69-92eb-41d1-a291-72b34df233e4
```
You can name it whatever you want. If we look back the `lsblk` output
```bash
lsblk -o name,uuid /dev/sda3
NAME                                        UUID
sda2                                        fa634f69-92eb-41d1-a291-72b34df233e4
└─luks-fa634f69-92eb-41d1-a291-72b34df233e4 
sda3                                        4809d477-1190-4ac3-aa4a-abf69d961578
└─luks-4809d477-1190-4ac3-aa4a-abf69d961578 6FBOVP-dDke-PZif-UpAZ-Fnnu-Ug2r-ZBSeJ4
  ├─centos_server-root                      d7718a14-a0d6-4401-8918-8eb0a862869f
  ├─centos_server-swap                      b4867c19-5744-48b8-b65f-34dc3c51b52b
  └─centos_server-home                      204b1e48-4035-4ea5-be30-d1b7849f0f21
```
we can see that the CentOS installer named our PV by taking the outer LUKS filesystem UUID (4809d477-1190-4ac3-aa4a-abf69d961578) and prepending it with luks-, giving us luks-4809d477-1190-4ac3-aa4a-abf69d961578. For the sake of consistency I've done the same, hence luks-fa634f69-92eb-41d1-a291-72b34df233e4.

5. Create a filesystem on the new partition. You can use any filesystem type known to GRUB.
```bash
mkfs -t xfs /dev/mapper/luks-fa634f69-92eb-41d1-a291-72b34df233e4
```

6. Mount the newly formatted partition to /boot
``` bash
mount -t xfs /dev/mapper/luks-fa634f69-92eb-41d1-a291-72b34df233e4 /boot
```

Before continuing, lets re-examine the output of `lsblk` for reference
```bash
lsblk -o name,type,size,uuid,fstype,mountpoint
NAME                                          TYPE    SIZE UUID                                   FSTYPE      MOUNTPOINT
sda                                           disk  465.8G                                                    
├─sda1                                        part      1M                                                    
├─sda2                                        part      1G fa634f69-92eb-41d1-a291-72b34df233e4   crypto_LUKS 
│ └─luks-fa634f69-92eb-41d1-a291-72b34df233e4 crypt  1022M d112beeb-98a0-4c7b-afee-d1774bceba51   xfs         /boot
└─sda3                                        part  464.8G 4809d477-1190-4ac3-aa4a-abf69d961578   crypto_LUKS 
  └─luks-4809d477-1190-4ac3-aa4a-abf69d961578 crypt 464.8G 6FBOVP-dDke-PZif-UpAZ-Fnnu-Ug2r-ZBSeJ4 LVM2_member 
    ├─centos_server-root                      lvm      50G d7718a14-a0d6-4401-8918-8eb0a862869f   xfs         /
    ├─centos_server-swap                      lvm     3.9G b4867c19-5744-48b8-b65f-34dc3c51b52b   swap        [SWAP]
    └─centos_server-home                      lvm   410.9G 204b1e48-4035-4ea5-be30-d1b7849f0f21   xfs         /home
```

7. Restore all of the previous /boot data
```bash
cp -a /boot-backup/. /boot/
diff -r /boot-backup /boot
rm -rf /boot-backup
```

8. Remove the old entry from /etc/fstab
```bash
sed -i '/UUID=550016b9-f79c-4176-be50-e753166fc58/d' /etc/fstab
```

9. Update /boot/grub2/cfg to inform grub that the boot partition (i.e. Stage 2) is encrypted.
```bash
echo 'GRUB_ENABLE_CRYPTODISK=y' >> /etc/default/grub
grub2-mkconfig -o /boot/grub2/grub.cfg
```

10. Reinstall grub. This will supply Stage 1.5 with the requisite modules to decrypt and mount the boot partition
```bash
grub2-install /dev/sda
```

Now during the boot process, before the kernel prompts you for the passphrase to unlock the root partition, GRUB Stage 1.5 will prompt you for the passphrase to unlock the boot partition.

To be clear, this does not entirely prevent the types of attacks mentioned above, but it does make them considerably more difficult. In a later post, we'll discuss adding initramfs hooks add even more protection.

#### Mounting the boot partition after the kernel starts
You may notice that after the boot sequence is complete, the boot partition (/dev/sda1) is not mounted to /boot. This is because you only gave the requisite passphrase to GRUB 1.5. The kernel, on the other hand, lacks this information; merely adding a corresponding entry to /etc/fstab will not suffice. Fortunately, in addition to interactive decryption, LUKS can decrypt devices using keyfiles, which presents a solution to this dilemma.

1. Create a keyfile
```bash
$ openssl rand 2048 -out /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key
$ chmod 400 /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key
```
2. Add the keyfile to the LUKS header on /dev/sda1 and test it
```bash
$ cryptsetup luksAddKey /dev/sda2 /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key
$ cryptsetup -v luksOpen --key-file /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key --test-passphrase /dev/sda2
Key slot 1 unlocked
Command successful
```

3. Update /etc/crypttab
```
echo 'luks-fa634f69-92eb-41d1-a291-72b34df233e4 UUID=fa634f69-92eb-41d1-a291-72b34df233e4 /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key luks' >> /etc/crypttab
```
Note that the fields are ${name_of_the_mount} UUID=${filesystem_uuid_of_encrypted_partition} ${path_to_keyfile} ${options}


4. Update /etc/fstab
```
echo 'UUID=d112beeb-98a0-4c7b-afee-d1774bceba51 /boot xfs defaults 0 2' >> /etc/fstab
```


### Prevent Laptop Suspensions/Sleep/Hiberation (Optional)
If, like me, you're using a laptop, you will likely want your server to continue running even if you close the lid of the laptop. To to do this,

1. Uncomment the `HandleLidSwitch` and `HandleLidSwitchDocked` properties /etc/systemd/logind.conf and set them to `ignore` 
```bash
$ sed -i -e 's/^#\(HandleLidSwitch= \).*$/^\1ignore$/' -e 's/^#\(HandleLidSwitchDocked= \).*$/^\1ignore$/' /etc/systemd/logind.conf
```

2. Restart `systemd-logind`
```bash
$ systemctl restart systemd-logind.service
```

## Troubleshooting

### Incorrectly entered boot partition passphrase
GRUB Stage 1.5 is rather simple. After all, it only has 32,256 bytes (i.e. the size of the post-MBR gap) in which to store its code. As such, if you incorrectly enter the passphrase for your newly created boot partition, GRUB will drop you into a rescue shell instead of reprompting you. 

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

### Other problems
Sometimes, you may encounter a problem which stops you from even reaching the GRUB rescue shell. For example, lets assume that in the boot partition encryption process, you forgot the final `grub2-install /dev/sda` command. In this case, the GRUB Stage 1.5 bootloader would lack the LUKS modules necessary to decrypt the boot partition. Since you can't boot the system into any sort of recovery shell, the solution is to boot from an external medium and correct the problem - which in this case would involve running `grub2-install /dev/sda`.

First, if you don't already have one, create a bootable USB flash drive like the one you used to install CentOS. This one doesn't need a GUI. One the OS is up and running, you'll need to recreate the environment of your actual HOST OS - we'll being does this on /mnt - before running the commands.

1. Decrypt the encrypted partitions
```bash
$ cryptsetup luksOpen /dev/sda1 luks-
$ cryptsetup luksOpen /dev/sda2 luks-
```

2. Mount the logical volumes and additional directories needed for `chroot` to function properly
```bash 
$ mount -t xfs /dev/centos/root /mnt
$ mount -t xfs /dev/centos/home /mnt/home
$ mount -t ext4 /dev/luks- /boot
$ swapon /dev/centos/swap
$ mount -t proc /mnt/proc/
$ mount --rbind /dev /mnt/dev/
$ mount --rbind /sys /mnt/sys/
$ mount --rbind /run /mnt/run/
```

3. Set your new root
```bash
$ chroot /mnt /bin/bash
```

4. Correct the error
```bash
$ grub2-install /dev/sda
```

Now reboot into your host system and everything should proceed normally.
