import requests
import pytest


def test_graph_initialization(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = [{'http://example.com/graph/upper': 'tests/upper_ontology.ttl',
                  'http://example.com/graph/domain': 'tests/domain_ontology.ttl',
                  'http://example.com/graph/instance': 'tests/instance_data.ttl'}]
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "select ?graph (count(?s) as ?size) where { graph ?graph { ?s ?p ?o } } group by ?graph"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    results = dict(
        (row['graph']['value'], row['size']['value'])
        for row in response.json()['results']['bindings'])

    expected = {'http://example.com/graph/upper': '18',
                'http://example.com/graph/domain': '21',
                'http://example.com/graph/instance': '15'}
    assert results == expected


def test_from_default(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = [{'http://example.com/graph/upper': 'tests/upper_ontology.ttl',
                  'http://example.com/graph/domain': 'tests/domain_ontology.ttl',
                  'http://example.com/graph/instance': 'tests/instance_data.ttl'}]
    endpoint = sparql_endpoint(repo_uri, rdf_files, default_graph_union=False)  # noqa: F841
    query = "select (count(?s) as ?size) where { ?s ?p ?o }"
    response = requests.get(url=repo_uri,
                            params={
                                'query': query,
                                'default-graph-uri': [
                                    'http://example.com/graph/upper',
                                    'http://example.com/graph/domain'
                                ]
                            },
                            headers={'Accept': 'application/json'})
    results = next((int(row['size']['value']) for row in response.json()['results']['bindings']), None)

    expected = 39
    assert results == expected


@pytest.mark.skip(reason="Wait for https://github.com/RDFLib/rdflib/issues/811 to be fixed")
def test_from_named(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = [{'http://example.com/graph/upper': 'tests/upper_ontology.ttl',
                  'http://example.com/graph/domain': 'tests/domain_ontology.ttl',
                  'http://example.com/graph/instance': 'tests/instance_data.ttl'}]
    endpoint = sparql_endpoint(repo_uri, rdf_files, default_graph_union=False)  # noqa: F841
    query = "select ?graph (count(?s) as ?size) where { graph ?graph { ?s ?p ?o } } group by ?graph"
    response = requests.get(url=repo_uri,
                            params={
                                'query': query,
                                'named-graph-uri': [
                                    'http://example.com/graph/upper',
                                    'http://example.com/graph/domain'
                                ]
                            },
                            headers={'Accept': 'application/json'})
    results = dict(
        (row['graph']['value'], row['size']['value'])
        for row in response.json()['results']['bindings'])

    expected = {'http://example.com/graph/upper': '18',
                'http://example.com/graph/domain': '21'}
    assert results == expected


@pytest.mark.skip(reason="No longer supported after rdflib 6.2.0")
def test_update_from_default(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = [{'http://example.com/graph/upper': 'tests/upper_ontology.ttl',
                  'http://example.com/graph/domain': 'tests/domain_ontology.ttl',
                  'http://example.com/graph/instance': 'tests/instance_data.ttl'}]
    endpoint = sparql_endpoint(repo_uri, rdf_files, default_graph_union=False)  # noqa: F841
    # Insert the count of triples in the default graph, which should be from the two
    # graphs provided only.
    query = "insert { <http://example.com/graph> <http://example.com/totalSize> ?size }" \
            " where { { select (count(?s) as ?size) where { ?s ?p ?o } } }"
    response = requests.get(url=repo_uri,
                            params={
                                'update': query,
                                'using-graph-uri': ['http://example.com/graph/upper', 'http://example.com/graph/domain']
                            })
    assert response.status_code == 200

    # Now read it back
    query = "select ?size where { <http://example.com/graph> <http://example.com/totalSize> ?size }"
    response = requests.get(url=repo_uri,
                            params={'query': query},
                            headers={'Accept': 'application/json'})
    results = next((int(row['size']['value']) for row in response.json()['results']['bindings']), None)

    expected = 39
    assert results == expected
