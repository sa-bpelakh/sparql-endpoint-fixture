import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sparql_endpoint_fixture",
    version="0.0.2",
    author="Boris Pelakh",
    author_email="boris.pelakh@semanticarts.com",
    description="SPARQL Endpoint Fixture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sa-bpelakh/sparql-endpoint-fixture",
    packages=setuptools.find_packages(),
    install_requires=[
        'rdflib[sparql]>=5.0.0',
        'SPARQLWrapper>=1.8.5',
        'pytest',
        'httpretty>=1.1.3'
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    package_data={
    },
    entry_points={
    },
    python_requires='>=3.7',
)
