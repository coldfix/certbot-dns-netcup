"""
The `~certbot_dns_netcup.dns_netcup` plugin automates the process of
completing a ``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and
subsequently removing, TXT records using the netcup CCP API.


Named Arguments
---------------

========================================  =====================================
``--dns-netcup-credentials``          netcup credentials_ INI file.
                                          (Required)
``--dns-netcup-propagation-seconds``  The number of seconds to wait for DNS
                                          to propagate before asking the ACME
                                          server to verify the DNS record.
                                          (Default: 10)
========================================  =====================================


Credentials
-----------

Use of this plugin requires a configuration file containing netcup API
credentials, obtained from your netcup
`account page <https://ccp.netcup.net/run/daten_aendern.php?sprung=api>`_.
See also the `CCP API <https://www.netcup-wiki.de/wiki/CCP_API>`_ documentation.

.. code-block:: ini
   :name: credentials.ini
   :caption: Example credentials file:

   # netcup API credentials used by Certbot
   dns_netcup_customer_id  = 123456
   dns_netcup_api_key      = 0123456789abcdef0123456789abcdef01234567
   dns_netcup_api_password = abcdef0123456789abcdef01234567abcdef0123
   dns_netcup_timeout      = 60

The path to this file can be provided interactively or using the
``--dns-netcup-credentials`` command-line argument. Certbot records the path
to this file for use during renewal, but does not store the file's contents.

The ``timeout`` entry can be used to avoid timeouts due to slow response times
of the netcup API servers. If this entry is not given it defaults to 60 seconds.

.. caution::
   You should protect these API credentials as you would the password to your
   netcup account. Users who can read this file can use these credentials
   to issue arbitrary API calls on your behalf. Users who can cause Certbot to
   run using these credentials can complete a ``dns-01`` challenge to acquire
   new certificates or revoke existing certificates for associated domains,
   even if those domains aren't being managed by this server.

Certbot will emit a warning if it detects that the credentials file can be
accessed by other users on your system. The warning reads "Unsafe permissions
on credentials configuration file", followed by the path to the credentials
file. This warning will be emitted each time Certbot uses the credentials file,
including for renewal, and cannot be silenced except by addressing the issue
(e.g., by using a command like ``chmod 600`` to restrict access to the file).


Examples
--------

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``

   certbot certonly \\
     --dns-netcup \\
     --dns-netcup-credentials ~/.secrets/certbot/netcup.ini \\
     -d example.com

.. code-block:: bash
   :caption: To acquire a single certificate for both ``example.com`` and
             ``www.example.com``

   certbot certonly \\
     --dns-netcup \\
     --dns-netcup-credentials ~/.secrets/certbot/netcup.ini \\
     -d example.com \\
     -d www.example.com

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``, waiting 60 seconds
             for DNS propagation

   certbot certonly \\
     --dns-netcup \\
     --dns-netcup-credentials ~/.secrets/certbot/netcup.ini \\
     --dns-netcup-propagation-seconds 60 \\
     -d example.com

"""
import nc_dnsapi
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

    description = ('Obtain certificates using a DNS TXT record (if you are using netcup for '
                   'DNS).')

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(add)
        add('credentials', help='netcup credentials INI file.')

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
               'the netcup API.'

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'netcup credentials INI file',
            {
                'customer-id': 'customer ID associated with netcup account',
                'api-key': 'API key for CCP API, see {0}'.format(CCP_API_URL),
                'api-password': 'API key for CCP API, see {0}'.format(CCP_API_URL),
            }
        )

    def _perform(self, domain, validation_name, validation):
        domain = '.'.join(domain.split('.')[-2:])
        with self._get_netcup_client() as api:
            api.add_dns_record(domain, _make_record(
                domain, validation_name, validation))

    def _cleanup(self, domain, validation_name, validation):
        domain = '.'.join(domain.split('.')[-2:])
        with self._get_netcup_client() as api:
            record = api.dns_record(domain, _make_record(
                domain, validation_name, validation))
            api.delete_dns_record(domain, record)

    def _get_netcup_client(self):
        credentials = self.credentials.conf
        return nc_dnsapi.Client(
            credentials('customer-id'),
            credentials('api-key'),
            credentials('api-password'),
            timeout=int(credentials('timeout') or 60))


def _make_record(domain, validation_name, validation):
    suffix = '.' + domain
    if validation_name.endswith(suffix):
        validation_name = validation_name[:-len(suffix)]
    return nc_dnsapi.DNSRecord(
        hostname=validation_name,
        type='TXT',
        destination=validation)
