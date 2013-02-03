from setuptools import setup, find_packages
import sys, os

setup(
    name="gsxws",
    version="0.2",
    description="Apple GSX integration.",
    install_requires = ['suds'],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: The BSD 2-Clause License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP"
    ],
    keywords="gsx, python",
    author="Filipp Lepalaan",
    author_email="filipp@mcare.fi",
    url="https://github.com/filipp/py-gsx",
    license="BSD",
    packages = find_packages(),
)
