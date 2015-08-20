from setuptools import setup

with open('./requirements.txt') as reqs_txt:
    requirements = [line for line in reqs_txt]

setup(
    name="flask-hyperschema",
    version="0.1.1",
    description="Flask Schema and Hyperschema Extension",
    author='Sukrit Khera',
    packages=['hyperschema'],
    install_requires=requirements,
    zip_safe=True,
    test_suite='tests',
    classifiers=[
        'Development Status :: In development',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities',
        'License :: The MIT License (MIT)',
        ],
    )
