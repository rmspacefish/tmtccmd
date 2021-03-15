import codecs
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(
    version=get_version("tmtccmd/core/__init__.py"),
    packages=['core', 'com_if', 'defaults', 'pus_tc', 'pus_tm', 'sendreceive', 'utility'],
)
