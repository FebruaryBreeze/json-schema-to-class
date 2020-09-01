"""
json-schema-to-class
Convert JSON Schema into Python Class
Author: SF-Zhou
Date: 2019-03-03
"""
from pathlib import Path

from setuptools import setup


class Package:
    name = 'json-schema-to-class'
    module = name.replace("-", "_")
    version = '0.2.3'
    description = 'Convert JSON Schema into Python Class'
    keywords = 'JSON Schema Class'
    package_data = {}
    entry_points = {
        'console_scripts': [
            f'{name}={module}:main',
            f'{name}-cli={module}:cli',
        ]
    }

    here = Path(Path(__file__).parent).absolute()
    with open(here / 'README.md') as f:
        long_description = f.read()

    with open(here / 'requirements.txt') as f:
        install_requires = f.read().splitlines()


setup(
    name=Package.name,
    version=Package.version,
    description=Package.description,
    long_description=Package.long_description,
    long_description_content_type='text/markdown',
    url=f'https://github.com/FebruaryBreeze/{Package.name}',
    license='MIT',
    author='SF-Zhou',
    author_email='sfzhou.scut@gmail.com',
    python_requires='>=3.6.0',
    keywords=Package.keywords,
    py_modules=[f'{Package.module}'],
    package_data=Package.package_data,
    entry_points=Package.entry_points,
    install_requires=Package.install_requires
)
