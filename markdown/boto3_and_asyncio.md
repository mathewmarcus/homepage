# Asynchronous AWS API calls with asyncio

## Problem
`boto3`, the AWS Python SDK, currently constitutes the primary API for interacting with the multitude of AWS services from Python. For all of its many capabilities, however, `boto3` - and its lower-level dependency `botocore` - are fundamentally synchronous and thus essentially incompatibile with `asyncio` coroutines. 

This can be somewhat limiting, because there often arises scenarios where we need to make a number of AWS service/API calls, wait for the results, and then further process the returned data. Performing each call in serial can waste time - if the call count is high - and while we could always use one of the `multiprocessing`, `threading`, or `concurrent.futures` modules, performing concurrent operations in this manner can inccur additional penalties because of the time/memory overhead involved in the creation of the threads/process.

For more info on the relative performance of synchronous, threaded, multiprocessed, and asynchronous python code, watch  [Shahriar Tajbakhsh's Parallelism Shootout presentation](https://www.youtube.com/watch?v=B0Qfe3U_hKU&feature=youtu.be), and for more general information on concurrency in Python, watch [this 2015 PyCon presentation](https://www.youtube.com/watch?v=MCs5OvhV9S4) by the inimitable David Beazly.


## Background
So what makes `boto3` and `botocore` incompatible with true aynciocoroutines - i.e. coroutines which do not simply offload work to other threads/processes via `asyncio.get_event_loop().run_in_executor(<some_boto3_call>)`? Well, in order to perform asynchronous network IO, the underlying sockets used by the library must be non-blocking, i.e. they must be created with the `SOCK_NONBLOCK` type or modified via a call to `fcntl` to have the file status flag of `O_NONBLOCK`

`botocore`, on the other hand, uses `urllib`(n) from the Python standard library which uses blocking sockets.


## Solution
At the lowest level all that `boto3`/`botocore` - or any of the AWS SKDS for that matter - provide us are convenience wrapper classes for making API calls to the AWS services via HTTP. 

So, the solution to the `boto3`-`asyncio` conundrum is to abandon boto3 altogether and to create the HTTP request from scratch, as detailed [here](https://docs.aws.amazon.com/lambda/latest/dg/API_Invoke.html), and then manually sign it, as detailed [here](https://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html#sig-v4-examples-post).


### Example
Lets envision a scenario where we want to spawn of n concurrent lambda requests. It just as easily  be any number of requests to any number of different AWS services, but for the purposes of simplicity we'll create 100 different requests to 100 different lambdas. If this were synchronous code, we would use the `boto3.client('lambda').invoke` method, but for async invocations we'll be creating the HTTPrequest(s) ourselves.


#### Requests
As mentioned earlier, we need to use non-blocking sockets in our HTTP requests. Luckily `aiohttp` is an excellent asynchronous HTTP library - redolent of the synchronous `requests` - which relieves us of the need to create these sockets ourselves.

For the purposes of this, we're going to define `function_and_payloads` as an iterable containing an arbitrary number of 2-tuples of type `(str, dict)` where the first element is the name of the AWS lambda function and the second is the payload. These correspond to the `FunctionName` and `Payload` arguments, respectively, of the `boto3.client('lambda').invoke` method described [here](http://boto3.readthedocs.io/en/latest/reference/services/lambda.html#Lambda.Client.invoke)

```python
import asyncio
from aiohttp import ClientSession

async def invoke(function_name, payload, session):
    url = 'https://lambda.us-east-1.amazonaws.com/2015-03-31/functions/{}/invocations'.format(function_name)
    async with session.post(url, json=payload) as response:
	    return await response.json()
		

async def invoke_all(functions_and_payloads):
    async with ClientSession(raise_for_status=True) as session:
	    invocations = (invoke(func_name, payload, session) for func_name, payload in functions_and_payloads)
		return await asyncio.gather(*invocations)
		
		
def invoke_all_wrapper(functions_and_payloads):
    loop = asyncio.get_event_loop()
	lambda_responses = loop.run_until_complete(invoke_all(functions_and_payloads))
```

A few things to note
1. `asyncio.gather` is used to return responses in the same order in which we invoked the lambdas, which is NOT necessarily the order in which they returned
2. We are assuming that we need data from ALL of the invoked lambdas in order to perform further processing; therefore if any of the lambdas fail we want to abort from the whole function. Consequently...
  a. the `raise_for_status=True` kwarg is passed to `aiohttp.ClientSession` to raise `aiohttp.client.ClientResponseError` if we receive a non-200 level HTTP status code from any of the lambdas
  b. When calling `asyncio.gather`, we use the default `return_exceptions=False`


#### Request Signing
We're missing one last piece: the signing of each request.

So, the final step is to create a function to sign each of the requests, i.e. generate the signed headers. For the sake of brevity I've used existing botocore functionality to accomplish this, but we could've just as easily used the process delineated in the above link.

```python
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session
from json import dumps

creds = Session().get_credentials()

def create_signed_headers(url, payload):
	request = AWSRequest(method='POST',
						 url=url,
						 data=dumps(payload))
	SigV4Auth(creds, 'lambda', 'us-east-1').add_auth(request)
	return dict(request.headers.items())
```

Now we just need to include these headers in each request like so. 

```python
async def invoke(function_name, payload, session):
    url = 'https://lambda.us-east-1.amazonaws.com/2015-03-31/functions/{}/invocations'.format(function_name)
	signed_headers = create_signed_headers(url, payload)
    async with session.post(url,
	                        json=payload,
							headers=signed_headers) as response:
	    return await response.json()
```


Below is the complete code with an example usage. Some sections have been condensed or otherwise modified for succinctness and extensibility. 


```python
import asyncio
from aiohttp import ClientSession

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session

from urllib.parse import urlparse
from os.path import join
from json import dumps


creds = Session().get_credentials()
LAMBDA_ENDPOINT_BASE = 'https://lambda.{region}.amazonaws.com/2015-03-31/functions'


def create_signed_headers(url, payload):
    host_segments = urlparse(url).netloc.split('.')
    service = host_segments[0]
    region = host_segments[1]
    request = AWSRequest(method='POST',
                         url=url,
                         data=dumps(payload))
    SigV4Auth(creds, service, region).add_auth(request)
    return dict(request.headers.items())


async def invoke(url, payload, session):
    signed_headers = create_signed_headers(url, payload)
    async with session.post(url,
                            json=payload,
                            headers=signed_headers) as response:
        return await response.json()


def generate_invocations(functions_and_payloads, base_url, session):
    for func_name, payload in functions_and_payloads:
        url = join(base_url, func_name, 'invocations')
        yield invoke(url, payload, session)


def invoke_all(functions_and_payloads, region='us-east-1'):
    base_url = LAMBDA_ENDPOINT_BASE.format(region=region)

    async def wrapped():
        async with ClientSession(raise_for_status=True) as session:
                invocations = generate_invocations(functions_and_payloads,
				                                   base_url,
												   session)
                return await asyncio.gather(*invocations)

    return asyncio.get_event_loop().run_until_complete(wrapped())


def main():
    func_name = 'hello-world-{}'
    funcs_and_payloads = ((func_name.format(i), dict(hello=i)) for i in range(100))

    lambda_responses = invoke_all(funcs_and_payloads)
	
	# Do some further processing with the responses


if __name__ == '__main__':
    main()
```

And to reiterate, although this example includes only lambda invocations, with the same header signing function and some simple modifications/additions to the `aiohttp` wrapper functions we could asynchronously call any number and variety of AWS services.
