from SPARQLWrapper import SPARQLWrapper, JSON
import pytest
import requests


@pytest.mark.skip(reason="urlopen wiring not yet done")
def test_basic_select(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    sparql = SPARQLWrapper(endpoint=repo_uri)
    query = "select distinct ?class where { [] a ?class } order by ?class"
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query()

    expected = endpoint.graph.query(query).serialize(format='json')
    assert results == expected


def test_request_get(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    query = "select distinct ?class where { [] a ?class } order by ?class"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    results = response.text

    expected = endpoint.graph.query(query).serialize(format='json').decode('utf-8')
    assert results == expected

    query = 'construct { <http://example.com/_t1> ?p ?o } where { <http://example.com/_t1> ?p ?o }'
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'text/turtle'})
    results = response.text

    expected = endpoint.graph.query(query).serialize(format='turtle').decode('utf-8')
    assert results == expected


def test_request_update_get(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    print(response.json())
    assert response.json()['results']['bindings'][0]['num']['value'] == '1'

    update = "insert { ?instance a ?super } " \
             "where { ?instance a/<http://www.w3.org/2000/01/rdf-schema#subClassOf> ?super }"
    response = requests.get(url=repo_uri, params={'update': update})
    assert response.status_code == 200

    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    assert response.json()['results']['bindings'][0]['num']['value'] == '3'


def test_request_update_post(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    print(response.json())
    assert response.json()['results']['bindings'][0]['num']['value'] == '1'

    update = "insert { ?instance a ?super } " \
             "where { ?instance a/<http://www.w3.org/2000/01/rdf-schema#subClassOf> ?super }"
    response = requests.post(url=repo_uri, data={'update': update})
    assert response.status_code == 200

    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    assert response.json()['results']['bindings'][0]['num']['value'] == '3'


def test_request_update_post_raw(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    print(response.json())
    assert response.json()['results']['bindings'][0]['num']['value'] == '1'

    update = "insert { ?instance a ?super } " \
             "where { ?instance a/<http://www.w3.org/2000/01/rdf-schema#subClassOf> ?super }"
    response = requests.post(url=repo_uri, data=update.encode('utf-8'),
                             headers={'Content-Type': 'application/sparql-update'})
    assert response.status_code == 200

    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    assert response.json()['results']['bindings'][0]['num']['value'] == '3'


def test_request_post(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    query = "select distinct ?class where { [] a ?class } order by ?class"
    response = requests.post(url=repo_uri, data={'query': query}, headers={'Accept': 'application/json'})
    results = response.text

    expected = endpoint.graph.query(query).serialize(format='json').decode('utf-8')
    assert results == expected


def test_request_post_raw(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    query = "select distinct ?class where { [] a ?class } order by ?class"
    expected = endpoint.graph.query(query).serialize(format='json').decode('utf-8')

    response = requests.post(url=repo_uri, data=query.encode('utf-8'),
                             headers={'Content-Type': 'application/sparql-query',
                                      'Accept': 'application/json'})
    results = response.text
    assert results == expected
