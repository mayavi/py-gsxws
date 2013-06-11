from setuptools import setup, find_packages

setup(
    name="gsxws",
    version="0.4",
    description="Apple GSX integration.",
    install_requires=['PyYAML'],
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
    author_email="filipp@fps.ee",
    url="https://github.com/filipp/py-gsxws",
    license="BSD",
    packages=find_packages(),
)
