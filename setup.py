"""
json-schema-to-class
Convert JSON Schema into Python Class
Author: SF-Zhou
Date: 2019-03-03
"""

from setuptools import setup

name = 'json-schema-to-class'
module = name.replace("-", "_")
setup(
    name=name,
    version='0.1.7',
    description='Convert JSON Schema into Python Class',
    url=f'https://github.com/FebruaryBreeze/{name}',
    author='SF-Zhou',
    author_email='sfzhou.scut@gmail.com',
    keywords='JSON Schema Class',
    entry_points={
        'console_scripts': [
            f'{name}={module}:main',
            f'{name}-cli={module}:cli',
        ],
    },
    py_modules=[f'{module}'],
    install_requires=['lazy-write']
)
