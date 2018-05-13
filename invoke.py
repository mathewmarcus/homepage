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
    """Asynchronously invoke an AWS Lambda

    Args:
       url (str): AWS Lambda endpoint
       payload (dict): JSON-style request body
       session (:obj: `aiohttp.ClientSession`)

    Returns:
        dict: AWS Lambda response payload

    Examples:
        >>> async def test():
                async with ClientSession() as session:
                    return await invoke('https://lambda.{region}.amazonaws.com/2015-03-31/functions/hello-world/invocations',
                                        {'hello': 'world'},
                                        session)
    """
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
                invocations = generate_invocations(functions_and_payloads, base_url, session)
                return await asyncio.gather(*invocations)

    return asyncio.get_event_loop().run_until_complete(wrapped())


def main():
    loop = asyncio.get_event_loop()
    print(loop.run_until_complete(foo()))
    # func_name = 'encirca-report-engine'
    # funcs_and_payloads = ((func_name, dict(hello=i)) for i in range(10))

    # lambda_responses = invoke_all(funcs_and_payloads)
    # print(lambda_responses)


if __name__ == '__main__':
    main()
