import os
from urllib.parse import parse_qs

import pytest
# import requests_mock
from rdflib import ConjunctiveGraph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import ParseException
from rdflib.plugins.sparql.parser import parseUpdate
from rdflib.util import guess_format
from requests import Request
from urllib3.response import HTTPResponse


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

        m.post(url=uri, raw=self.handle_post)
        m.get(url=uri, raw=self.handle_get)

        # TODO handle GET/PUT/DELETE/POST/HEAD/PATCH for Graph Protocol
        # https://www.w3.org/TR/2013/REC-sparql11-http-rdf-update-20130321/

    def handle_post(self, request: Request, context: dict) -> HTTPResponse:
        if request.headers['content-type'] == 'application/x-www-form-urlencoded':
            parsed = parse_qs(request.data)
            if 'query' in parsed:
                return self.process_query(parsed['query'][0], results_format=request.headers.get('accept'),
                                          graph_uris=parsed.get('using-graph-uri'),
                                          named_graph_uris=parsed.get('using-named-graph-uri'))
            elif 'update' in parsed:
                return self.process_update(parsed['update'][0],
                                           graph_uris=parsed.get('using-graph-uri'),
                                           named_graph_uris=parsed.get('using-named-graph-uri'))
        elif request.headers['content-type'] == 'application/sparql-query':
            return self.process_query(request.data, results_format=request.headers.get('accept'),
                                      graph_uris=request.params.get('using-graph-uri'),
                                      named_graph_uris=request.params.get('using-named-graph-uri'))
        elif request.headers['content-type'] == 'application/sparql-update':
            return self.process_update(request.data,
                                       graph_uris=request.params.get('using-graph-uri'),
                                       named_graph_uris=request.params.get('using-named-graph-uri'))

    def handle_get(self, request: Request, context: dict) -> HTTPResponse:
        if 'query' in request.params:
            return self.process_query(request.params['query'], results_format=request.headers.get('accept'),
                                      graph_uris=request.params.get('using-graph-uri'),
                                      named_graph_uris=request.params.get('using-named-graph-uri'))
        elif 'update' in request.params:
            return self.process_update(request.params['update'],
                                       graph_uris=request.params.get('using-graph-uri'),
                                       named_graph_uris=request.params.get('using-named-graph-uri'))

        return HTTPResponse(body="Unable to parse request", status=400)

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
        'application/json': 'json',
        'application/ld+json': 'json',
        'application/rdf+xml': 'xml'
    }

    def process_query(self, query, results_format=None, graph_uris=None, named_graph_uris=None):
        try:
            parsed_query = prepareQuery(query)
        except ParseException as pe:
            return HTTPResponse(body=f"Malformed UPDATE: {pe} in {query}", status=400)
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
            return HTTPResponse(body=f"Unsupported result type {results_format}", status=415)

        try:
            results = self.graph.query(parsed_query)
            if parsed_query.algebra.name == 'SelectQuery':
                return HTTPResponse(body=results.serialize(format=mapped_format),
                                    headers={'content-type': results_format},
                                    status=200)
            elif parsed_query.algebra.name == 'ConstructQuery':
                return HTTPResponse(body=results.graph.serialize(format=mapped_format),
                                    headers={'content-type': results_format},
                                    status=200)
            else:
                return HTTPResponse(body=str(results.askAnswer),
                                    headers={'content-type': results_format},
                                    status=200)
        except Exception as e:
            return HTTPResponse(body=f"Error {e} occurred when evaluating {query}", status=500)

    def process_update(self, query, graph_uris=None, named_graph_uris=None):
        try:
            parsed_query = translateUpdate(parseUpdate(query))
        except ParseException as pe:
            return HTTPResponse(body=f"Malformed UPDATE: {pe} in {query}", status=400)

        # TODO patch query.algebra.datasetClause with graph_uris (FROM) and named_graph_uris (FROM NAMED)

        try:
            self.graph.update(parsed_query)
        except Exception as e:
            return HTTPResponse(body=f"Error {e} occurred when evaluating {query}", status=500)
        return HTTPResponse(body=f"Updated", status=200)


@pytest.fixture
def sparql_endpoint(requests_mock):
    yield lambda uri, initial_data: Endpoint(requests_mock, uri, initial_data)
