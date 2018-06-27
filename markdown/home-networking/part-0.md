# Introduction
This purpose of this tutorial series is to demonstrate one approach to setting up a home network. These initial tutorials will detail the setup and administration of a network built on Linux servers. That said, for the most part, clients of any OS type (OSX, Windows, or Linux) will be able to join and use the services on this network (more on that in later tutorials). The creation and administration of a Windows Active Directory (AD) domain will be covered in an entirely seperate tutorial series.


### Linux Server Distros
In an attempt to use a distro similar to that commonly found in enterprise envrionments (Red Hat), we'll be using CentOS for these tutorials. Additionally, given that I also run Arch on several of my servers, I will also include alternate Arch-specific instructions when they differ.


### Hardware
I'm using a number of Virtualbox VMs as well as a wide variety of hardware in my networkk - ranging from an old Dell Inspiron laptop to an assortment of Raspberry Pi's - so don't feel as though you need anything particular/special.


### Scripting
After the initial setup, all of the subsequent steps will be recorded in Ansible playbooks for the sake of clarity and reproducibility.


### Table of Contents
0. Introduction
1. Server Installation and Initial Setup
  1. [Basic Installation](/blog/building-a-home-network/part-1a.html)
  2. [Securing the Boot Process](/blog/building-a-home-network/part-1b.html)
2. Gateway Router and Subnet Setup
<!-- 3. [DNS] -->
<!-- 4. [DHCP] -->
<!-- 5. [DHCP Client] -->
<!-- 6. [LDAP] -->
<!-- 7. [Kerberos] -->
<!-- 8. [NFS] -->
<!-- 9. Kodi -->
<!-- 10. [Samba] -->
<!-- 11. [Web server] -->
<!-- 12. [Cameras] -->
