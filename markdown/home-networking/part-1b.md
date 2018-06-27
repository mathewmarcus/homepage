# Securing the Boot Process

In this tutorial we'll build on the install from the previous tutorial and further harden the physical security of our installs by encrypting the boot partition. 

## Encrypting the boot partition
Encrypting the root partition is an excellent step, but only the first one. An unencrypted boot partition opens you up to an Evil Maid attack. The details of this attack are beyond the scope of this post, but essentially because the boot partition is unencrypted an attacker with physical access to your machine could, with relative ease, install a bootkit by replacing or modifying:
1. any one of the GRUB Stage 2 modules
2. the initial ramdisk (initramfs) or any of the files in it
3. the kernel itself

By encrypting the boot partition we can attempt to stave off - or at the very least hinder - these types of attacks.

1. Backup all the data on your existing boot partition and verify that the contents are identical
   ```bash
   $ mkdir /boot-backup
   $ cp -a /boot/. /boot-backup
   $ diff -r /boot /boot-backup
   ```

2. Unmount the existing boot partition
   ```bash
   $ umount /boot
   ```

3. Create the new LUKS partition on /dev/sda2 (i.e. the current boot partition) ***This will overwrite filesystem info on the existing boot partition***
   ```bash
   $ cryptsetup luksFormat --verify-passphrase /dev/sda2
   ```

4. Decrypt and mount the partition.

   ```bash
   $ cryptsetup luksOpen /dev/sda2 luks-fa634f69-92eb-41d1-a291-72b34df233e4
   ```
You can name it whatever you want. If we look back the `lsblk` output
   ```bash
   $ lsblk -o name,uuid /dev/sda3
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
   $ mkfs -t xfs /dev/mapper/luks-fa634f69-92eb-41d1-a291-72b34df233e4
   ```

6. Mount the newly formatted partition to /boot
   ```bash
   $ mount -t xfs /dev/mapper/luks-fa634f69-92eb-41d1-a291-72b34df233e4 /boot
   ```
Before continuing, lets examine the new output of `lsblk` for reference
   ```bash
   $ lsblk -o name,type,size,uuid,fstype,mountpoint
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
  $ cp -a /boot-backup/. /boot/
  $ diff -r /boot-backup /boot
  $ rm -rf /boot-backup
  ```

8. Remove the old entry from /etc/fstab
   ```bash
   $ sed -i '/UUID=550016b9-f79c-4176-be50-e753166fc58/d' /etc/fstab
   ```

9. Update /boot/grub2/grub.cfg to inform GRUB that the boot partition (i.e. Stage 2) is encrypted.
   ```bash
   $ echo 'GRUB_ENABLE_CRYPTODISK=y' >> /etc/default/grub
   $ grub2-mkconfig -o /boot/grub2/grub.cfg
   ```

10. Reinstall GRUB. This will supply Stage 1.5 with the requisite modules to decrypt and mount the boot partition

	```bash
	$ grub2-install /dev/sda
	```

Now during the boot process, before the kernel prompts you for the passphrase to unlock the root partition, GRUB Stage 1.5 will prompt you for the passphrase to unlock the boot partition.

To be clear, this does not entirely prevent the types of attacks mentioned above, but it does make them considerably more difficult. In a later post, we'll discuss adding initramfs hooks to add even more protection.

### Mounting the boot partition after the kernel starts
You may notice that after the boot sequence is complete, the boot partition (luks-fa634f69-92eb-41d1-a291-72b34df233e4) is not mounted to /boot, nor is it even decrypted. This is because you only gave the requisite passphrase to GRUB 1.5. The kernel, on the other hand, lacks this information; merely adding a corresponding entry to /etc/fstab will not suffice. Fortunately, in addition to interactive decryption, LUKS can decrypt devices using keyfiles, which presents a solution to this dilemma.

1. Create a keyfile and ensure only the root user can read it.
   ```bash
   $ openssl rand 2048 -out /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key
   $ chmod 400 /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key
   ```

2. Add the keyfile to the LUKS header on /dev/sda2 and test it
   ```bash
   $ cryptsetup luksAddKey /dev/sda2 /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key
   $ cryptsetup -v luksOpen --key-file /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key --test-passphrase /dev/sda2
   Key slot 1 unlocked
   Command successful
   ```

3. Update /etc/crypttab
   ```bash
   $ echo 'luks-fa634f69-92eb-41d1-a291-72b34df233e4 UUID=fa634f69-92eb-41d1-a291-72b34df233e4 /etc/luks-fa634f69-92eb-41d1-a291-72b34df233e4.key luks' >> /etc/crypttab
   ```
Note that the fields are ${name_of_the_mount} UUID=${filesystem_uuid_of_encrypted_partition} ${path_to_keyfile} ${options}


4. Update /etc/fstab
   ```bash
   $ echo 'UUID=d112beeb-98a0-4c7b-afee-d1774bceba51 /boot xfs defaults 0 2' >> /etc/fstab
   ```
   Note that here we identify the boot partiition not by its name, luks-fa634f69-92eb-41d1-a291-72b34df233e4, but by it's filesystem UUID, as shown in the above `lsblk` output.

## Troubleshooting

### Incorrectly entered boot partition passphrase
GRUB Stage 1.5 is rather simple. After all, it only has 32,256 bytes (i.e. the size of the post-MBR gap) in which to store its code. As such, if you incorrectly enter the passphrase for your newly created boot partition, GRUB will drop you into a rescue shell instead of reprompting you. 

Far more limited than its Stage 2 analog, the GRUB rescue shell contains only a handful of commands which, unfortunately, do not include `help` or `?`. However, the boot sequence can still be resumed with the following commands.

1. Unlock and mount the boot partition (/dev/sda2)
   ```bash
   grub-rescue> cryptomount (hd0,msdos2)
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

First, if you don't already have one, create a bootable USB flash drive like the one you used to install CentOS. It one doesn't need a GUI. Once the OS is up and running, you'll need to recreate the environment of your actual HOST OS - we'll be doing this on /mnt - before running the commands.

1. Decrypt the encrypted partitions
   ```bash
   $ cryptsetup luksOpen /dev/sda2 luks-fa634f69-92eb-41d1-a291-72b34df233e4
   $ cryptsetup luksOpen /dev/sda3 luks-4809d477-1190-4ac3-aa4a-abf69d961578
   ```

2. Mount the logical volumes and additional directories needed for `chroot` to function properly
   ```bash 
   $ mount -t xfs /dev/centos/root /mnt
   $ mount -t xfs /dev/centos/home /mnt/home
   $ mount -t xfs /dev/mapper/luks-fa634f69-92eb-41d1-a291-72b34df233e4 /boot
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


## What's Next
In the next tutorial, we'll set up our gateway router and subnets.
