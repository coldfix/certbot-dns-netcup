"""
This module defines a certbot plugin to automate the process of completing a
``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and subsequently
removing, TXT records using the netcup CCP API.
"""

# Keep metadata before any imports (for setup.py)!
__version__ = '1.5.0'
__url__     = 'https://github.com/coldfix/certbot-dns-netcup'
__all__     = ['Authenticator']

from certbot.plugins import dns_common_lexicon


CCP_API_URL = 'https://www.netcup-wiki.de/wiki/CCP_API'


class Authenticator(dns_common_lexicon.LexiconDNSAuthenticator):
    """DNS Authenticator for netcup

    This Authenticator uses the netcup API to fulfill a dns-01 challenge.
    """

    description = ('Obtain certificates using a DNS TXT record (if you are '
                   'using netcup for DNS).')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._add_provider_option(
            'customer-id',
            'Customer ID associated with netcup account',
            'auth_customer_id')
        self._add_provider_option(
            'api-key',
            'Key for CCP API, see {}'.format(CCP_API_URL),
            'auth_api_key')
        self._add_provider_option(
            'api-password',
            'Password for CCP API, see {}'.format(CCP_API_URL),
            'auth_api_password')

    @classmethod
    def add_parser_arguments(cls, add):
        super().add_parser_arguments(add, default_propagation_seconds=900)
        add('credentials', help='netcup credentials INI file.')

    def more_info(self):
        return ('This plugin configures a DNS TXT record to respond to a '
                'dns-01 challenge using the netcup API.')

    @property
    def _provider_name(self):
        return 'netcup'

    # called while guessing domain name (going from most specific to tld):
    def _handle_general_error(self, e, domain_name):
        if 'Value in field domainname does not match requirements' in str(e):
            return None
        return super()._handle_general_error(e, domain_name)
