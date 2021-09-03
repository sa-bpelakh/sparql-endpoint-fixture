import requests


def test_missing_query_get(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "select distinct ?class where { [] a ?class } order by ?class"
    response = requests.get(url=repo_uri, params={'wrong': query}, headers={'Accept': 'application/json'})

    assert response.status_code == 400


def test_bad_result_format(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "select distinct ?class where { [] a ?class } order by ?class"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/unknown'})

    assert response.status_code == 415


def server_fail():
    raise Exception('Fake Server Failure')


def test_query_eval_error(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    endpoint.graph.query = server_fail
    query = "select distinct ?class where { [] a ?class } order by ?class"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})

    assert response.status_code == 500


def test_update_eval_error(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    endpoint.graph.update = server_fail
    update = "insert { ?instance a ?super } " \
             "where { ?instance a/<http://www.w3.org/2000/01/rdf-schema#subClassOf> ?super }"
    response = requests.post(url=repo_uri, data=update.encode('utf-8'),
                             headers={'Content-Type': 'application/sparql-update'})
    assert response.status_code == 500


def test_missing_query_post(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "select distinct ?class where { [] a ?class } order by ?class"
    response = requests.post(url=repo_uri, data={'wrong': query}, headers={'Accept': 'application/json'})

    assert response.status_code == 400


def test_post_bad_content(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    update = "insert { ?instance a ?super } " \
             "where { ?instance a/<http://www.w3.org/2000/01/rdf-schema#subClassOf> ?super }"
    response = requests.post(url=repo_uri, data=update.encode('utf-8'),
                             headers={'Content-Type': 'application/bad-content-type'})
    assert response.status_code == 415


def test_malformed_query(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    query = "definitely not a SPARQL query"
    response = requests.get(url=repo_uri, params={'query': query}, headers={'Accept': 'application/json'})

    assert response.status_code == 400


def test_malformed_update(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/sparql'
    rdf_files = ['tests/upper_ontology.ttl']
    endpoint = sparql_endpoint(repo_uri, rdf_files)  # noqa: F841
    update = "definitely not a SPARQL update"
    response = requests.get(url=repo_uri, params={'update': update}, headers={'Accept': 'application/json'})

    assert response.status_code == 400
