# sparql-endpoint-fixture
## RDFLIB-based SPARQL Endpoint Fixture for pytest

Enable the fixture explicitly in your tests or conftest.py (not required when using setuptools entry points):

```python
pytest_plugins = [
    "sparql_endpoint_fixture.endpoint"
]
```

The endpoint fixture uses [httpretty](https://pypi.org/project/httpretty/) to intercept
all HTTP calls to the specified URL and can be initialized with RDF data 
prior to use. 

```python
def test_request_get(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)
    query = "select distinct ?class where { [] a ?class } order by ?class"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})
    assert len(response.json()['results']['bindings']) == '10'
```

Since the backing store for the simulated endpoint is a 
[RDFLib ConjuntiveGraph](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.graph.ConjunctiveGraph),
initial data can be loaded into specified named graphs:

```python
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
```

