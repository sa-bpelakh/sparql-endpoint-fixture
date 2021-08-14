import os
from urllib.parse import urlparse, parse_qs

import pytest
# import requests_mock
from rdflib import ConjunctiveGraph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import ParseException
from rdflib.plugins.sparql.parser import parseUpdate
from rdflib.util import guess_format
from requests import Request


class Endpoint:

    def load_rdf(self, rdf_file_or_text: str, graph: str = None):
        rdf_format = 'turtle'
        if os.path.isfile(rdf_file_or_text):
            rdf_format = guess_format(rdf_file_or_text)
            rdf = open(rdf_file_or_text, "r").read()
        else:
            rdf = rdf_file_or_text
        if graph:
            self.graph.get_context(graph).parse(data=rdf, format=rdf_format)
        else:
            # Default graph
            self.graph.parse(data=rdf, format=rdf_format)

    def __init__(self, m, uri: str, initial_data: list):
        self.mocker = m
        self.graph = ConjunctiveGraph()
        for arg in initial_data:
            if isinstance(arg, dict):
                for graph_name, payload in arg:
                    self.load_rdf(payload, graph=graph_name)
            else:
                self.load_rdf(arg)

        m.post(url=uri, text=self.handle_post)
        m.get(url=uri, text=self.handle_get)

        # TODO handle GET/PUT/DELETE/POST/HEAD/PATCH for Graph Protocol
        # https://www.w3.org/TR/2013/REC-sparql11-http-rdf-update-20130321/

    def handle_post(self, request: Request, context) -> str:
        # Want the raw string, because mocker lower-cases
        parsed = urlparse(request._request.url)
        qs = parse_qs(parsed.query)
        content_type = request.headers['Content-Type']
        if content_type == 'application/x-www-form-urlencoded':
            parsed_body = parse_qs(request.text)
            if 'query' in parsed_body:
                status, headers, text = \
                    self.process_query(parsed_body['query'][0], results_format=request.headers.get('Accept'),
                                       graph_uris=qs.get('using-graph-uri'),
                                       named_graph_uris=qs.get('using-named-graph-uri'))
            elif 'update' in parsed_body:
                status, headers, text = \
                    self.process_update(parsed_body['update'][0],
                                        graph_uris=qs.get('using-graph-uri'),
                                        named_graph_uris=qs.get('using-named-graph-uri'))
            else:
                status, headers, text = 400, {}, "Unable to parse request body"
        elif content_type == 'application/sparql-query':
            status, headers, text = \
                self.process_query(request.text, results_format=request.headers.get('Accept'),
                                   graph_uris=qs.get('using-graph-uri'),
                                   named_graph_uris=qs.get('using-named-graph-uri'))
        elif content_type == 'application/sparql-update':
            status, headers, text = \
                self.process_update(request.text,
                                    graph_uris=qs.get('using-graph-uri'),
                                    named_graph_uris=qs.get('using-named-graph-uri'))
        else:
            status, headers, text = 415, {}, f"Unrecognized content type: {content_type}"

        context.status_code = status
        if status != 200:
            context.reason = text
        context.headers.update(headers)

        return text

    def handle_get(self, request: Request, context) -> str:
        # Want the raw string, because mocker lower-cases
        parsed = urlparse(request._request.url)
        qs = parse_qs(parsed.query)
        if 'query' in qs:
            status, headers, text = \
                self.process_query(qs['query'][0], results_format=request.headers.get('Accept'),
                                   graph_uris=qs.get('using-graph-uri'),
                                   named_graph_uris=qs.get('using-named-graph-uri'))
        elif 'update' in qs:
            status, headers, text = \
                self.process_update(qs['update'][0],
                                    graph_uris=qs.get('using-graph-uri'),
                                    named_graph_uris=qs.get('using-named-graph-uri'))
        else:
            status, headers, text = 400, {}, "Unable to parse request"

        context.status_code = status
        if status != 200:
            context.reason = text
        context.headers.update(headers)

        return text

    TABLE_MEDIA_TYPES = {
        'text/plain': 'txt',
        'text/tab-separated-values': 'txt',
        'text/csv': 'csv',
        'application/json': 'json',
        'application/sparql-results+json': 'json',
        'application/sparql-results+xml': 'xml'
    }

    RDF_MEDIA_TYPES = {
        'text/plain': 'txt',
        'text/csv': 'csv',
        'text/turtle': 'turtle',
        'application/json': 'json',
        'application/ld+json': 'json',
        'application/rdf+xml': 'xml'
    }

    def process_query(self, query, results_format=None,
                      graph_uris=None, named_graph_uris=None) -> (int, dict, str):
        try:
            parsed_query = prepareQuery(query)
        except ParseException as pe:
            return 400, {}, f"Malformed query: {pe} in {query}"
        # TODO patch query.algebra.datasetClause with graph_uris (FROM) and named_graph_uris (FROM NAMED)
        # parsed_query.algebra.name will be SelectQuery, ConstructQuery or AskQuery
        if parsed_query.algebra.name == 'SelectQuery':
            if results_format is None:
                results_format = 'application/sparql-results+xml'
            mapped_format = self.TABLE_MEDIA_TYPES.get(results_format)
        elif parsed_query.algebra.name == 'ConstructQuery':
            if results_format is None:
                results_format = 'application/rdf+xml'
            mapped_format = self.RDF_MEDIA_TYPES.get(results_format)
        else:
            # Ask
            if results_format is None:
                results_format = 'text/plain'
            mapped_format = self.TABLE_MEDIA_TYPES.get(results_format)

        if mapped_format is None:
            return 415, {}, f"Unsupported result type {results_format}"

        try:
            results = self.graph.query(parsed_query)
            if parsed_query.algebra.name == 'SelectQuery':
                return 200, {'Content-type': results_format}, \
                       results.serialize(format=mapped_format).decode('utf-8')
            elif parsed_query.algebra.name == 'ConstructQuery':
                return 200, {'Content-type': results_format}, \
                       results.graph.serialize(format=mapped_format)
            else:
                return 200, {'content-type': results_format}, str(results.askAnswer)
        except Exception as e:
            return 500, {}, f"Error {e} occurred when evaluating {query}"

    def process_update(self, query, graph_uris=None, named_graph_uris=None) -> (int, dict, str):
        try:
            parsed_query = translateUpdate(parseUpdate(query))
        except ParseException as pe:
            return 400, {}, f"Malformed UPDATE: {pe} in {query}"

        # TODO patch query.algebra.datasetClause with graph_uris (FROM) and named_graph_uris (FROM NAMED)

        try:
            self.graph.update(parsed_query)
        except Exception as e:
            return 500, {}, f"Error {e} occurred when evaluating {query}"
        return 200, {}, "Updated"


@pytest.fixture
def sparql_endpoint(requests_mock):
    yield lambda uri, initial_data: Endpoint(requests_mock, uri, initial_data)
