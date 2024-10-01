from setuptools import find_packages, setup

setup(
    name='djangordf',
    packages=find_packages(include=['djangordf']),
    version='0.1.0',
    description='A RDF library for Django models',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Deine Lizenz
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    author='Benjamin Schnabel',
    email='b.schnabel@hs-mannheim.de',
    website='djangordf.readthedocs.org',
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/judaicalink/djangordf",
    install_requires=[],
    setup_requires=['pytest-runner'],
    tests_require=['pytest==7.4.4'],
    test_suite='tests',
)