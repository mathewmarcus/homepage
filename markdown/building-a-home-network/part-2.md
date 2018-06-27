BIND options
------------
	forwarders { 1.0.0.1, 8.8.8.8 }
	forward-only
	
Why? Now rather than loading our router by demanding that it perform recursive queryies, we allow it to perform an iterative query to the fast, secure 1.0.0.1 public cloudflare DNS resolver, however we still get all the caching benefits


script everything with ansible
systemd-network files

Idea:
	turn 0f 20-resolv.conf dhcpcd hook
	use custom hook to systemd-resolve --set-dns and --set-domain instead
	set env wireless_ssid=
	use wireless_ssid to start wpa_suppliciant -c /etc/wpa_supplicant/${wireless_ssid}.conf
	then start dhcpcd on corresponding interface
