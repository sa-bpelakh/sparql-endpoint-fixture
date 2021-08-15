from SPARQLWrapper import SPARQLWrapper, JSON, POST
import json
import requests


def test_wrapper_select(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    sparql = SPARQLWrapper(endpoint=repo_uri)
    query = "select distinct ?class where { [] a ?class } order by ?class"
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    expected = json.loads(endpoint.graph.query(query).serialize(format='json'))
    assert results == expected


def test_wrapper_ask(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    sparql = SPARQLWrapper(endpoint=repo_uri)
    query = "ASK { ?instance a ?class }"
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    expected = json.loads(endpoint.graph.query(query).serialize(format='json'))
    assert results == expected


def test_wrapper_update(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841

    sparql = SPARQLWrapper(endpoint=repo_uri)
    sparql.setReturnFormat(JSON)
    sparql.setMethod(POST)

    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    sparql.setQuery(query)
    results = sparql.query().convert()
    assert results['results']['bindings'][0]['num']['value'] == '1'

    update = "insert { ?instance a ?super } " \
             "where { ?instance a/<http://www.w3.org/2000/01/rdf-schema#subClassOf> ?super }"
    sparql.setQuery(update)
    results = sparql.query()
    assert results.info()['status'] == '200'

    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    sparql.setQuery(query)
    results = sparql.query().convert()
    assert results['results']['bindings'][0]['num']['value'] == '3'


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


def test_multiple_graphs(sparql_endpoint):
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


def test_request_update_get(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
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
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
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
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "select (count(?person) as ?num) where { ?person a <http://example.com/Person> }"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
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
