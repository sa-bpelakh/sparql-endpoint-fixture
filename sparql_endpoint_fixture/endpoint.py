"""pytest fixture for a HTTP SPARQL endpoint."""
import os
import re
from typing import Dict, Tuple, List, Callable, Union
from urllib.parse import parse_qs, urlparse

import httpretty
import pytest
from httpretty.core import HTTPrettyRequest
from pyparsing import ParseException
from rdflib import ConjunctiveGraph, URIRef
from rdflib.plugins import sparql as sparql_options
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.util import guess_format

# Requests result in a return code, headers and body
RequestResult = Tuple[int, Dict[str, str], str]
Handler = Callable[[HTTPrettyRequest], RequestResult]
PredefinedResponse = Union[RequestResult, Handler]

class Endpoint:
    """Handles SPARQL read/write queries."""

    def load_rdf(self, rdf_file_or_text: str, graph: str = None):
        """Load RDF data into graph."""
        rdf_format = 'turtle'
        if os.path.isfile(rdf_file_or_text):
            rdf_format = guess_format(rdf_file_or_text)
            with open(rdf_file_or_text, "r", encoding='utf-8') as rdf_file:
                rdf = rdf_file.read()
        else:
            rdf = rdf_file_or_text
        if graph:
            self.graph.get_context(graph).parse(data=rdf, format=rdf_format)
        else:
            # Default graph
            self.graph.parse(data=rdf, format=rdf_format)

    def __init__(self, uri: str, initial_data: list, **kwargs):
        self.predefined = kwargs.get('predefined', {})
        self.graph = ConjunctiveGraph()
        # To work in isolation, disable loading external data
        sparql_options.SPARQL_LOAD_GRAPHS = False
        if 'default_graph_union' in kwargs:
            sparql_options.SPARQL_DEFAULT_GRAPH_UNION = kwargs['default_graph_union']
        for arg in initial_data:
            if isinstance(arg, dict):
                for graph_name, payload in arg.items():
                    self.load_rdf(payload, graph=graph_name)
            else:
                self.load_rdf(arg)

        httpretty.register_uri(httpretty.GET, uri,
                               body=self._handle_get)
        httpretty.register_uri(httpretty.POST, uri,
                               body=self._handle_post)

        # TODO handle GET/PUT/DELETE/POST/HEAD/PATCH for Graph Protocol
        # https://www.w3.org/TR/2013/REC-sparql11-http-rdf-update-20130321/

    def _predefined_value(self, path: str) -> PredefinedResponse:
        """Determine if path is an exact or regex match for a predefined handler."""
        if self.predefined:
            print('Matching ', path, ' against ', self.predefined)
        if path in self.predefined:
            return self.predefined[path]
        return next(
            (value
             for regex, value in self.predefined.items()
             if isinstance(regex, re.Pattern) and regex.fullmatch(path)),
            None)

    def _predefined_response(
        self,
        predefined_response: PredefinedResponse,
        request: HTTPrettyRequest) -> RequestResult:
        """Determine a static or dynamic predefined response."""
        print('Applying ', predefined_response, ' to ', request)
        if callable(predefined_response):
            applied = predefined_response(request)
            print('Callable returned ', applied)
            return applied
        return predefined_response

    def _handle_post(self, request: HTTPrettyRequest,
                    url: str,
                    ret_headers: dict) -> list:
        # Want the raw string, because mocker lower-cases
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        content_type = request.headers['Content-Type']
        predefined_match = self._predefined_value(parsed.path)
        if predefined_match is not None:
            status, headers, text = self._predefined_response(predefined_match, request)
        elif content_type == 'application/x-www-form-urlencoded':
            parsed_body = parse_qs(request.body.decode('utf-8'))
            if 'query' in parsed_body:
                status, headers, text = \
                    self._process_query(parsed_body['query'][0], results_format=request.headers.get('Accept'),
                                       graph_uris=qs.get('default-graph-uri'),
                                       named_graph_uris=qs.get('named-graph-uri'))
            elif 'update' in parsed_body:
                status, headers, text = \
                    self._process_update(parsed_body['update'][0],
                                        graph_uris=qs.get('using-graph-uri'),
                                        named_graph_uris=qs.get('using-named-graph-uri'))
            else:
                status, headers, text = 400, {}, "Unable to parse request body"
        elif content_type == 'application/sparql-query':
            status, headers, text = \
                self._process_query(request.body.decode('utf-8'), results_format=request.headers.get('Accept'),
                                   graph_uris=qs.get('default-graph-uri'),
                                   named_graph_uris=qs.get('named-graph-uri'))
        elif content_type == 'application/sparql-update':
            status, headers, text = \
                self._process_update(request.body.decode('utf-8'),
                                    graph_uris=qs.get('using-graph-uri'),
                                    named_graph_uris=qs.get('using-named-graph-uri'))
        else:
            status, headers, text = 415, {}, f"Unrecognized content type: {content_type}"

        ret_headers.update(headers)
        return [status, ret_headers, text]

    def _handle_get(self, request: HTTPrettyRequest,
                   url: str,
                   ret_headers: dict) -> list:
        # Want the raw string, because mocker lower-cases
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        predefined_match = self._predefined_value(parsed.path)
        if predefined_match is not None:
            status, headers, text = self._predefined_response(predefined_match, request)
        elif 'query' in qs:
            status, headers, text = \
                self._process_query(qs['query'][0], results_format=request.headers.get('Accept'),
                                   graph_uris=qs.get('default-graph-uri'),
                                   named_graph_uris=qs.get('named-graph-uri'))
        elif 'update' in qs:
            status, headers, text = \
                self._process_update(qs['update'][0],
                                    graph_uris=qs.get('using-graph-uri'),
                                    named_graph_uris=qs.get('using-named-graph-uri'))
        else:
            status, headers, text = 400, {}, "Unable to parse request"

        ret_headers.update(headers)
        return [status, ret_headers, text.encode('utf-8')]

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

    ASK_MEDIA_TYPES = {
        'application/json': 'json',
        'application/sparql-results+xml': 'xml'
    }

    @staticmethod
    def _resolve_media_type(table, all_types, default=None):
        return next((table.get(choice) for choice in (all_types or default).split(',') if choice in table), None)

    def _process_query(self, query, results_format=None,
                      graph_uris=None, named_graph_uris=None) -> Tuple[int, dict, str]:
        try:
            parsed_query = prepareQuery(query)
        except ParseException as pe:
            return 400, {}, f"Malformed query: {pe} in {query}"

        # Replace query dataset clause with graph_uris (FROM) and named_graph_uris (FROM NAMED)
        # No attempt is made to merge the dataset clause already in the query with graph names
        # provided in the request parameters
        if graph_uris is not None or named_graph_uris is not None:
            parsed_query.algebra.datasetClause = \
                [CompValue(name='DatasetClause', vars=set(), default=URIRef(uri)) for uri in (graph_uris or [])] + \
                [CompValue(name='DatasetClause', vars=set(), named=URIRef(uri)) for uri in (named_graph_uris or [])]

        # parsed_query.algebra.name will be SelectQuery, ConstructQuery or AskQuery
        if parsed_query.algebra.name == 'SelectQuery':
            mapped_format = self._resolve_media_type(self.TABLE_MEDIA_TYPES, results_format,
                                                    'application/sparql-results+xml')
        elif parsed_query.algebra.name == 'ConstructQuery':
            mapped_format = self._resolve_media_type(self.RDF_MEDIA_TYPES, results_format,
                                                    'application/rdf+xml')
        else:
            # Ask
            mapped_format = self._resolve_media_type(self.ASK_MEDIA_TYPES, results_format,
                                                    'application/sparql-results+xml')

        if mapped_format is None:
            return 415, {}, f"Unsupported result type {results_format}"

        try:
            results = self.graph.query(parsed_query)
            if parsed_query.algebra.name == 'SelectQuery':
                return 200, {'Content-type': results_format}, \
                       results.serialize(format=mapped_format).decode('utf-8')
            if parsed_query.algebra.name == 'ConstructQuery':
                return 200, {'Content-type': results_format}, \
                       results.graph.serialize(format=mapped_format)
            return 200, {'Content-type': results_format}, \
                    results.serialize(format=mapped_format).decode('utf-8')
        except Exception as e:
            return 500, {}, f"Error {e} occurred when evaluating {query}"

    def _process_update(self, query, graph_uris=None, named_graph_uris=None) -> (int, dict, str):
        try:
            parsed_query = translateUpdate(parseUpdate(query))
        except ParseException as pe:
            return 400, {}, f"Malformed UPDATE: {pe} in {query}"

        # Replace query USING clause with graph_uris (FROM) and named_graph_uris (FROM NAMED)
        # No attempt is made to merge the USING clause already in the query with graph names
        # provided in the request parameters
        if graph_uris is not None or named_graph_uris is not None:
            parsed_query.algebra[0].datasetClause = \
                [CompValue(name='DatasetClause', vars=set(), default=URIRef(uri)) for uri in (graph_uris or [])] + \
                [CompValue(name='DatasetClause', vars=set(), named=URIRef(uri)) for uri in (named_graph_uris or [])]
            print(parsed_query.__dict__)

        try:
            self.graph.update(parsed_query)
        except Exception as e:
            return 500, {}, f"Error {e} occurred when evaluating {query}"
        return 200, {}, "Updated"


@pytest.fixture
def sparql_endpoint():
    """Enable request interception, disable on teardown."""
    httpretty.set_default_thread_timeout(60)
    httpretty.enable(verbose=True,
                     allow_net_connect=False)  # enable HTTPretty so that it will monkey patch the socket module

    yield lambda uri, initial_data, **kwargs: Endpoint(uri, initial_data, **kwargs)

    httpretty.disable()  # disable afterwards, so that you will have no problems in code that uses that socket module
    httpretty.reset()  # reset HTTPretty state (clean up registered urls and request history)
