from setuptools import find_packages, setup

setup(
    name='djangordf',
    packages=find_packages(include=['djangordf', 'djangordf.*']),
    version='0.5.0',
    description='A RDF library for Django models',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    author='Benjamin Schnabel',
    author_email='b.schnabel@hs-mannheim.de',
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/judaicalink/djangordf",
    project_urls={
        "Documentation": "https://djangordf.readthedocs.io/",
        "Source": "https://github.com/judaicalink/djangordf",
    },
    install_requires=[
        "Django>=3.2",
        "rdflib>=6.0",
        "requests>=2.25",
    ],
)
