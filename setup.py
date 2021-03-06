#!/usr/bin/env python

from setuptools import setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name='slicker',
    version='0.9.3',
    description='A tool for moving python files.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Khan Academy',
    author_email='opensource+pypi@khanacademy.org',
    url='https://github.com/Khan/slicker',
    keywords=['codemod', 'refactor', 'refactoring'],
    packages=['slicker'],
    install_requires=['asttokens==1.1.8', 'tqdm==4.19.5', 'fix-includes==0.2'],
    entry_points={
        # setuptools magic to make a `slicker` binary
        'console_scripts': ['slicker = slicker.slicker:main'],
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
)
