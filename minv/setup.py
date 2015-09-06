
import os.path
from setuptools import setup, find_packages


def find_files(base_path):
    for dirpath, _, filenames in os.walk(base_path):
        for filename in filenames:
            yield os.path.join(dirpath, filename)


setup(
    name='minv',
    version="0.0.1",
    description='MInv - Master Inventory',
    author='Fabian Schindler',
    author_email='fabian.schindler@eox.at',
    url='',
    packages=find_packages(),
    scripts=[
    ],
    include_package_data=True,
    package_data={
        '': [
            "*.html", "*.css", "*.js", "*.eot", "*.svg",
            "*.woff", "*.woff2", "*.ttf"
        ]
    },
)
