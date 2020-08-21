#!/usr/bin/env python3

from setuptools import setup

setup(
    name='coursewatch',
    version='1.2.4',
    description='Discord bot to watch availability of courses on Ellucian Banner',
    author='Rishov Sarkar',
    url='https://github.com/ArkaneMoose/CourseWatch',
    license='MIT',
    packages=['coursewatch'],
    install_requires=[
        'discord.py >=1.4.1, <2.0.0',
        'google-api-python-client >=1.6.2, <1.7.0',
        'termcolor >=1.1.0, <2.0.0',
        'tldextract >=2.1.0, <3.0.0',
        'PyYAML >=5.3.1, <6.0.0',
        'beautifulsoup4 >=4.6.0, <5.0.0',
        'humanize >=0.5.1, <0.6.0',
    ],
    entry_points={
        'console_scripts': [
            'coursewatch = coursewatch.main:main',
        ]
    },
    zip_safe=True
)
