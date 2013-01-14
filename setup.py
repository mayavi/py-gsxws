from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='py-gsx',
    version=version,
    description="Apple GSX integration.",
    long_description='',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: The BSD 2-Clause License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP'
    ],
    keywords='gsx, python',
    py_modules=['py-gsx'],
    author='Filipp Lepalaan',
    author_email='filipp@mcare.fi',
    url='https://github.com/filipp/py-gsx',
    license='BSD',
)
