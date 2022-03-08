"""Setup script for boringproxy API"""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    README = readme_file.read()

# This call to setup() does all the work
setup_args = dict(
    name="boringproxy-api",
    version="0.2.1",
    description="Simplify boringproxy service management",
    long_description=README,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages(),
    author="Aitor Iturrioz",
    author_email="riturrioz@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3"
    ],
    url='https://github.com/bodiroga/boringproxy-python-api',
    download_url='https://pypi.org/project/boringproxy-api/'
)

install_requires = [
    'requests==2.27.1',
    'beautifulsoup4==4.10.0'
]

if __name__ == '__main__':
    setup(install_requires=install_requires, **setup_args)
