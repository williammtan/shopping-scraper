import re
from graphql.parser import GraphQLParser
from scrapy.utils.project import get_project_settings
import scrapy
import json
import shlex


class BaseSpiderGQL(object):
    # custom_settings = {
    #     'SPIDER_MIDDLEWARES': {
    #         'shopping.middlewares.TokpedGQLSpiderMiddleware': 543,
    #     }
    # }

    def parse_split(self, response, args=None, **kwargs):
        data = response.json()
        if args == None:
            yield from self.parse(data['data'], **kwargs)
        else:
            for i in range(len(data)):
                yield from self.parse(data[i]['data'], **args[i])


class TokpedGQL():
    operation_name = 'example_operation_name'
    query = 'example_query_name'
    url = 'https://gql.tokopedia.com/'
    request_cue = []
    request_cue_length = 100

    def __init__(self, operation_name, query, default_variables={}):
        request_cue_length = get_project_settings()['REQUEST_CUE']
        self.operation_name = operation_name
        self.query = query
        self.default_variables = default_variables
        self.request_cue_length = request_cue_length
        self.parser = GraphQLParser()
        self.i = -1

    def convert(self, o):
        if isinstance(o, np.int64):
            return int(o)
        raise TypeError

    def parse_split(self, response, cb_kwargs, callbacks):
        data = response.json()
        for i in range(len(data)):
            callbacks(data[i], **cb_kwargs[i])

    def request(self, callback, headers={}, cb_kwargs=None, **kwargs):
        input_variables = kwargs
        # overide default vars
        vars = self.default_variables
        for k, v in input_variables.items():
            vars[k] = v

        body = {
            'operationName': self.operation_name,
            'variables': vars,
            'query': self.query
        }
        json_body = json.dumps(body)

        headers_base = {'content-type': 'application/json',
                        'referer': 'aaaa', 'x-device': 'desktop'}
        headers_base.update(headers)
        self.i+=1
        return scrapy.FormRequest(url=self.url, method='POST', body=json_body, headers=headers_base, callback=callback, cb_kwargs=cb_kwargs, meta={'cookie_jar': self.i})

    def merge_requests(self, requests):
        """Merge request bodies by taking the other parameters from the first request"""
        body = [json.loads(r.body) for r in requests]
        json_body = json.dumps(body)

        new_request = requests[0]
        new_request = new_request.replace(body=json_body, cb_kwargs={'args': [r.cb_kwargs for r in requests]})

        return new_request


def compress_graphql(q):
    """Compress a GraphQL query by removing unnecessary whitespace.

    >>> compress_graphql(query_with_strings)
    u'query someQuery { Field( search: "string with   spaces" ) { foo } }'
    """
    return u' '.join(shlex.split(q, posix=False))