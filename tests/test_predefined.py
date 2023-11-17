import re
import requests


def test_request_get(sparql_endpoint):
    repo_uri = 'https://my.rdfdb.com/repo/'
    rdf_files = ['tests/upper_ontology.ttl',
                 'tests/domain_ontology.ttl',
                 'tests/instance_data.ttl']
    endpoint = sparql_endpoint(
        re.compile(repo_uri + '.*'),
        rdf_files,
        predefined={
            # Fixed match, fixed response
            '/repo/ok': (200, {}, 'OK'),
            # Regex match, fixed response
            re.compile(r'/repo/transaction/.*'): (201, {}, ''),
            # Regex match, dynamic response
            re.compile(r'/repo/admin/.*'): lambda r: (200, {}, r.path[15:])
        }
    )
    response = requests.get(url=repo_uri+'ok')
    assert response.status_code == 200

    response = requests.get(url=repo_uri+'transaction/start')
    assert response.status_code == 201

    payload = {'optimize': True}
    response = requests.post(url=repo_uri+'admin/db/test', data=payload)
    assert response.status_code == 200
    assert response.text == 'test'

    response = requests.get(url=repo_uri+'/unknown')
    assert response.status_code == 400
