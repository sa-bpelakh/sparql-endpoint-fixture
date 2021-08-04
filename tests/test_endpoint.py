from SPARQLWrapper import SPARQLWrapper, JSON


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
