import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sparql_endpoint_fixture",
    version="1.0.0",
    author="Boris Pelakh",
    author_email="boris.pelakh@semanticarts.com",
    description="SPARQL Endpoint Fixture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sa-bpelakh/sparql-endpoint-fixture",
    packages=setuptools.find_packages(),
    license="bsd-3-clause",
    platforms=["any"],
    install_requires=[
        'rdflib>=6.2.0',
        'SPARQLWrapper~=1.8.5',
        'requests~=2.24.0',
        'pytest>=7.0.0',
        'httpretty~=1.1.3'
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: BSD License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "Natural Language :: English",
    ],
    package_data={
    },
    entry_points={
    },
    python_requires='>=3.9',
)
