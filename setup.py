"""Setup script for LC-ICP-MS Data Viewer."""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='lcicpms-ui',
    version='0.2.0',
    author='Christian Dewey',
    author_email='',
    description='A PyQt5 application for analyzing LC-ICP-MS chromatography data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/deweycw/LCICPMS-ui',
    packages=find_packages(exclude=['tests', 'tests.*']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-qt>=4.0.0',
            'mypy>=0.950',
            'black>=22.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'lcicpms-ui=uiGenerator.__main__:main',
        ],
    },
    include_package_data=True,
)
