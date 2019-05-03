"""
This module defines a certbot plugin to automate the process of completing a
``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and subsequently
removing, TXT records using the netcup CCP API.
"""

# Keep metadata before any imports (for setup.py)!
__version__ = '0.27.0.dev6'
__url__     = 'https://github.com/coldfix/certbot-dns-netcup'
__all__     = ['Authenticator']

from lexicon.config import ConfigResolver
from lexicon.providers import netcup
import zope.interface

from certbot import interfaces
from certbot.plugins import dns_common

CCP_API_URL = 'https://www.netcup-wiki.de/wiki/CCP_API'


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for netcup

    This Authenticator uses the netcup API to fulfill a dns-01 challenge.
    """

    description = ('Obtain certificates using a DNS TXT record (if you are '
                   'using netcup for DNS).')

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):
        super(Authenticator, cls).add_parser_arguments(add)
        add('credentials', help='netcup credentials INI file.')

    def more_info(self):
        return ('This plugin configures a DNS TXT record to respond to a '
                'dns-01 challenge using the netcup API.')

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'netcup credentials INI file',
            {
                'customer-id':  'Customer ID associated with netcup account',
                'api-key':      'Key for CCP API, see {}'.format(CCP_API_URL),
                'api-password': 'Password for CCP API, see {}'.format(CCP_API_URL),
            }
        )

    def _perform(self, domain, validation_name, validation):
        self._get_netcup_client(domain).create_record(
            'TXT', validation_name, validation)

    def _cleanup(self, domain, validation_name, validation):
        self._get_netcup_client(domain).delete_record(
            None, 'TXT', domain, validation_name, validation)

    def _get_netcup_client(self, domain):
        conf = self.credentials.conf
        provider = netcup.Provider(ConfigResolver().with_dict({
            'provider_name': 'netcup',
            'domain': '.'.join(domain.split('.')[-2:]),
            'netcup': {
                'auth_customer_id':   conf('customer-id'),
                'auth_api_key':       conf('api-key'),
                'auth_api_password':  conf('api-password'),
            },
        }).with_env())
        provider.authenticate()
        return provider
