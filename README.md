# flask-hyperschema
=================

Provides integration of Json Schema and Json HyperSchema with Python Flask.

## Development Status
This library is currently under development.

## Documentation
Project uses Sphinx for code/api dpcumentation

### Location
The latest code/api documentation can be found at:
[http://flask-hyperschema.readthedocs.org/](http://flask-hyperschema.readthedocs.org/)

### Building documentation
To generate html documentation, use command: 

```
cd docs && make html
```

The documentation will be generated in docs/build folder.

## Requirements

The project has following dependencies  
- python 2.7.x or python 3.4.x
  
### Dependencies

To install dependencies for the project, run command:  

```
pip install requirements.txt
```

In addition if you are developing on the project, run command: 

```
pip install dev-requirements.txt
```

## Testing

Tests are located in tests folder. Project uses nose for testing.

### Unit Tests

To run all unit tests , run command :

```
nosetests -w tests/unit
```

## Coding Standards and Guidelines

### flake8
In order to ensure that code follows PEP8 standards, run command: 

```
flake8 .
```
