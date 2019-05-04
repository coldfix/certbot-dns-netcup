# encoding: utf-8
from setuptools import setup


version = '0.27.0.dev6'

install_requires = [
    'acme>=0.21.1',
    'certbot>=0.21.1',
    'nc_dnsapi>=0.1.5',
    'zope.interface',
]


with open('README.rst', 'rb') as f:
    long_description = f.read().decode('utf-8')


setup(
    name='certbot-dns-netcup',
    version=version,
    description="netcup DNS Authenticator plugin for Certbot",
    long_description=long_description,
    url='https://github.com/coldfix/certbot-dns-netcup',
    author="Thomas Gläßle",
    author_email='thomas@coldfix.de',
    license='Apache License 2.0',
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],

    py_modules=['certbot_dns_netcup'],
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        'certbot.plugins': [
            'dns-netcup = certbot_dns_netcup:Authenticator',
        ],
    },
)
