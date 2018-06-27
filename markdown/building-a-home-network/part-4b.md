if systemd-resolved is in enabled
	if readlink /etc/resolv.conf == /run/systemd/resolv/stub-resolv.conf || readlink /etc/resolv.conf == /run/systemd/resolv/resolv.conf
		systemd-resolved is NOT updated with info in /etc/resolv.conf:
			TEST: systemd-resolve --status
	else:
		systemd-resolve IS updated with info from /etc/resolv.conf
			EXAMPLE:
				when dhcpcd updates /etc/resolvc.conf
				
				
				
dhcpcd:
	/usr/lib/dhcpcd/dhcpcd-hooks/29-lookup-hostname -> /usr/share/dhcpcd/dhcpcd-hooks/29-lookup-hostname
		This does a PTR (reverse) query on the new IP to check if hostname was set in DDNS
			if yes:, hostname env variable is set
				thus, even if the dhcp server doesn't send back a hostname, we will get the correct one
	/usr/lib/dhcpcd/dhcpcd-hooks/30-hostname
	        if hostname env variable is set and domain-name variable is set (from dhcp server)
				fqdn hostname is updated
			elif hostname env variable is set
				hostname is updated
			elif hostname is not set and force_hostname=YES
				hostname is set to localhost
			else:
				hostname is unmodified
				

systemd-resolved is aware of calls to hostname


systemd resolved solves the /etc/resolv.conf problem. No clients can interact with it to get DNSSEC, caching, and other useful features. they can communicate with it via:
	DBUS API
	linux C API (e.g. getaddrinfo) (BUT no DNSSEC)
	stub listener on 127.0.0.53:53
		this is exposed in /run/systemd/resolve/stub-resolv.conf which can be symlinked from /etc/resolv.conf as mentioned above
		
		
systemd file preference order
	/etc/resolv.conf IF IT IS NOT a symlink to one of the files in /run/systemd/resolve/
	[Network] section in /etc/systemd/*network files 
	/etc/systemd/resolved.conf
	
systemd-resolved can also be manually updated on a per interface basis via systemd-resolve -i ${interface} --set-dns=${dns_server} [--set-domain=${domain_name}]

systemd-resolved can be queried (like dig) like so
	systemd-resolve [--type=${DNS_RESOURCE_TYPE}] ${domain}
	
systemd-resolved can support DNSSEC if enabled in one of the files in systemd file preference order above
	reccomended value is allow-downgrade to support resolvers which don't support DNSSEC (BIND9 DOES support it)
		this is subject to protocol downgrade attacks
		
	
