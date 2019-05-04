# encoding: utf-8
from setuptools import setup


def exec_file(path):
    """Execute a python file and return the `globals` dictionary."""
    with open(path, 'rb') as f:
        code = compile(f.read(), path, 'exec')
    namespace = {}
    try:
        exec(code, namespace, namespace)
    except ImportError:     # ignore missing dependencies at setup time
        pass                # and return dunder-globals anyway!
    return namespace


metadata = exec_file('certbot_dns_netcup.py')

setup(
    version = metadata['__version__'],
    url     = metadata['__url__'],
)
