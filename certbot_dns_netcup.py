"""
This module defines a certbot plugin to automate the process of completing a
``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and subsequently
removing, TXT records using the netcup CCP API.
"""

# Keep metadata before any imports (for setup.py)!
__version__ = '1.3.1'
__url__     = 'https://github.com/coldfix/certbot-dns-netcup'
__all__     = ['Authenticator']

from lexicon.providers import netcup

from certbot.plugins import dns_common
from certbot.plugins import dns_common_lexicon

try:                    # certbot 1.x, required until <=1.17
    import zope.interface
    from certbot.interfaces import IAuthenticator, IPluginFactory

    def implement_authenticator(cls):
        cls = zope.interface.provider(IPluginFactory)(cls)
        cls = zope.interface.implementer(IAuthenticator)(cls)
        return cls
except ImportError:     # certbot 2.x, compatible with >=1.18
    def implement_authenticator(cls):
        return cls


CCP_API_URL = 'https://www.netcup-wiki.de/wiki/CCP_API'


@implement_authenticator
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
        self._get_netcup_client().add_txt_record(
            domain, validation_name, validation)

    def _cleanup(self, domain, validation_name, validation):
        self._get_netcup_client().del_txt_record(
            domain, validation_name, validation)

    def _get_netcup_client(self):
        credentials = self.credentials.conf
        return _NetcupLexiconClient(
            credentials('customer-id'),
            credentials('api-key'),
            credentials('api-password'))


class _NetcupLexiconClient(dns_common_lexicon.LexiconClient):
    """Encapsulates all communication with netcup via Lexicon."""

    def __init__(self, customer_id, api_key, api_password):
        super(_NetcupLexiconClient, self).__init__()
        config = dns_common_lexicon.build_lexicon_config('netcup', {}, {
            'auth_customer_id':   customer_id,
            'auth_api_key':       api_key,
            'auth_api_password':  api_password,
        })
        self.provider = netcup.Provider(config)

    # called while guessing domain name (going from most specific to tld):
    def _handle_general_error(self, e, domain_name):
        if 'Value in field domainname does not match requirements' in str(e):
            return None
        return super(_NetcupLexiconClient, self)._handle_general_error(
            e, domain_name)
