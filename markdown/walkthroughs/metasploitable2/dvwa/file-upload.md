# File Inclusion

## Easy

### Exploit
This one is pretty basic. Just choose any one of the webshells /usr/share/webshell/php/, upload it, and browse to it in /dvwa/hackackble/uploads/. We also could have used another type of shell (bind/reverse).

### Code Analysis
This is a basic file upload <form>.

```html
 <form enctype="multipart/form-data" action="#" method="POST" />
	 <input type="hidden" name="MAX_FILE_SIZE" value="100000" />
	 Choose an image to upload:
	 <br />
	 <input name="uploaded" type="file" /><br />
	 <br />
	 <input type="submit" name="Upload" value="Upload" />
 </form>
```

Note that in the below PHP code, the `Upload` parameter is checked in the outermost conditional and thus must be present in the POST request; this is important to note if we wanted to send this request outside of the browser with a different HTTP client (e.g. curl). 

```php
if (isset($_POST['Upload'])) { 

		$target_path = DVWA_WEB_PAGE_TO_ROOT."hackable/uploads/"; 
		$target_path = $target_path . basename( $_FILES['uploaded']['name']); 

		if(!move_uploaded_file($_FILES['uploaded']['tmp_name'], $target_path)) { 

			echo '<pre>'; 
			echo 'Your image was not uploaded.'; 
			echo '</pre>'; 

		  } else { 

			echo '<pre>'; 
			echo $target_path . ' succesfully uploaded!'; 
			echo '</pre>'; 

		} 

	} 
```

## Medium

## Code Analysis
If we try to upload a PHP webshell as in the previous example, we receive an error message telling us that our file was not uploaded. If we examine the request using the browser network tab or Burp Proxy we that in addition to the file contents, the request body includes the content type which, in this case, is application/php. It's reasonable to assume that perhaps the server is expecting a content type of image/jpeg, and perhaps is even - unadvisadly - using this value to perform validation.

Examining the below code confirms this; the code is using the browser supplied type to validate the image. This browser can implicitly determine this value based on the file, or it can be set explicitly via the `accept` attribute of an `<input>` (e.g. `<input name="uploaded" type="file" accept=image/jpeg>`). Most importantly, since it is supplied by the client, it can be easily spoofed and thus should not be used for server-side validation. 

```php
 if (isset($_POST['Upload'])) { 

		 $target_path = DVWA_WEB_PAGE_TO_ROOT."hackable/uploads/"; 
		 $target_path = $target_path . basename($_FILES['uploaded']['name']); 
		 $uploaded_name = $_FILES['uploaded']['name']; 
		 $uploaded_type = $_FILES['uploaded']['type']; 
		 $uploaded_size = $_FILES['uploaded']['size']; 

		 if (($uploaded_type == "image/jpeg") && ($uploaded_size < 100000)){ 


			 if(!move_uploaded_file($_FILES['uploaded']['tmp_name'], $target_path)) { 

				 echo '<pre>'; 
				 echo 'Your image was not uploaded.'; 
				 echo '</pre>'; 

			   } else { 

				 echo '<pre>'; 
				 echo $target_path . ' succesfully uploaded!'; 
				 echo '</pre>'; 

				 } 
		 } 
		 else{ 
			 echo '<pre>Your image was not uploaded.</pre>'; 
		 } 
	 } 
```

## Exploit
The solution is to tailor an HTTP request to pass these checks.

```bash
curl --cookie 'security=medium; PHPSESSID=e2ccc471d913ae972ed0c3e5c8663886' \
	 --form MAX_FILE_SIZE=100000
	 --form Upload=Upload
	 --form 'uploaded=@/usr/share/webshells/php/backdoor.php;type=image/jpeg'
     http://192.168.56.6/dvwa/vulnerabilities/upload/
```

The key option is `--form 'uploaded=@/usr/share/webshells/php/backdoor.php;type=image/jpeg'`. Here we specify the webshell, but spoof the type by setting it to `image/jpeg` in order to accomodate the `if (($uploaded_type == "image/jpeg")` check. We also include the other form fields as well the session cookie to prove that we're authenticated. Now just browse to the webshell in /dvwa/hackable/uploads/. As in the previous example, we also could have used another type of shell (bind/reverse).


## High

### Code Analysis

Examination of the below PHP code reveals that in this case, the file extension of the uploaded file is used to perform validation.

```php
if (isset($_POST['Upload'])) { 

            $target_path = DVWA_WEB_PAGE_TO_ROOT."hackable/uploads/"; 
            $target_path = $target_path . basename($_FILES['uploaded']['name']); 
            $uploaded_name = $_FILES['uploaded']['name']; 
            $uploaded_ext = substr($uploaded_name, strrpos($uploaded_name, '.') + 1); 
            $uploaded_size = $_FILES['uploaded']['size']; 

            if (($uploaded_ext == "jpg" || $uploaded_ext == "JPG" || $uploaded_ext == "jpeg" || $uploaded_ext == "JPEG") && ($uploaded_size < 100000)){ 


                if(!move_uploaded_file($_FILES['uploaded']['tmp_name'], $target_path)) { 
                     
                    echo '<pre>'; 
                    echo 'Your image was not uploaded.'; 
                    echo '</pre>'; 
                 
                  } else { 
                 
                    echo '<pre>'; 
                    echo $target_path . ' succesfully uploaded!'; 
                    echo '</pre>'; 
                     
                    } 
            } 
             
            else{ 
                 
                echo '<pre>'; 
                echo 'Your image was not uploaded.'; 
                echo '</pre>'; 

            } 
        } 
```

Specifically, we can see from the second conditional that that the file extension must be one of jpg, JPG, jpeg, or JPEG. The vulnerability resides in the statement used to determine this extension: `substr($uploaded_name, strrpos($uploaded_name, '.') + 1);`. `strrpos` is a PHP function used to determine the LAST index of a substring in a string - in this case the substring is `"."` and the larger string is the name of the file. The code does not, however, check that the file contains only one extension (i.e. one occurence of `"."`). As long as the final extension is one of jpg, JPG, jpeg, or JPEG, the file is accepted. 

### Exploit

By taking one of the previously used {web,reverse,bind} shells and appending it with a jpeg file extension, we can successfully upload our file. As before, all we need to do is browse to the file in /dvwa/hackable/uploads/.

Why does this work? If the final file extension indicates that the file is an image, why does the webserver - which in this case in Apache - still execute it as a PHP script? To understand this, we need to undetstand a bit about how Apache works. The important lines reside in the `/etc/apache2/mods-enabled/php.conf`.

```apache
...
AddHandler php-cgi .php
Action php-cgi /cgi-bin/php
...
```

The first directive intructs Apache to use the `php-cgi` handler for all files with a `.php` extension. The second directive instructs the `php-cgi` handler to execute matched files as CGI scripts using `/cgi-bin/php` (i.e. the PHP interpreter). So, all files ending with a `.php` extension will treated as CGI PHP scripts to be executed. According to the [Apache AddHandler Directive docs](https://httpd.apache.org/docs/2.4/mod/mod_mime.html#addhandler).
> Filenames may have multiple extensions and the extension argument will be compared against each of them.
So as long as the file contains the `.php` substring, Apache will treat it as CGI PHP script.

### Solutions
There are several possible solutions to this problem.

#### 1. Limit the directories in which CGI scripts are executed.
Currently the following line in the `/etc/apache2/mods-enabled/php.conf`

```apache
Options +ExecCGI
```

instructs Apache to permit execution of CGI scripts IN ALL DIRECTORIES. This is generally unecessary; instead, execution of CGI scripts should be restricted to specific directories by placing the `Options +ExecCGI` directive inside specific blocks (e.g.`<Directory></Directory>`, `<Location></Location>`, etc). In our case, even if a malicious user did succeed in bypassing the server-side validation and uploading a PHP script to /dvwa/hackable/uploads/, as long as we didn't add `ExecCGI` as one of the directory options, the script would not be executed.


#### 2. Restring the handler to files which END with the extension
Instead of using the `AddHandler` directive, we could replace it with

```apache
<FilesMatch "[^.]+\.php$">
  <SetHandler php-cgi>
</FilesMatch
```

This will ensure that only files which end with `.php` will be executed. So our case, even if a malicious user bypassed the validation by uploading `backdoor.php.jpeg`, this file would not match the above regex and thus would NOT be treated as a CGI PHP script.
