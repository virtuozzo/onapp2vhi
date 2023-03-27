from distutils.core import setup
from setuptools import setup, find_packages

setup(
    name='onapp2vhi',
    version='0.1dev0',
    author='Virtuozzo',
    author_email='onapp2vhi@virtuzzo.com',
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "onapp2vhi = onapp2vhi.main:run",
        ]
    },
    long_description=open('README.md').read()
)
