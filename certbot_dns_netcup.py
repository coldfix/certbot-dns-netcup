"""
This module defines a certbot plugin to automate the process of completing a
``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and subsequently
removing, TXT records using the netcup CCP API.
"""

# Keep metadata before any imports (for setup.py)!
__version__ = '1.5.0'
__url__     = 'https://github.com/coldfix/certbot-dns-netcup'
__all__     = ['Authenticator']

import json
import logging
import requests

from certbot.plugins import dns_common
from certbot.errors import PluginError


API_URL = 'https://www.netcup-wiki.de/wiki/CCP_API'
API_ENDPOINT = "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"

LOGGER = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for netcup

    This Authenticator uses the netcup API to fulfill a dns-01 challenge.
    """

    description = ('Obtain certificates using a DNS TXT record (if you are '
                   'using netcup for DNS).')

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None
        self.api_session_id = None

    # DNSAuthenticator overrides

    @classmethod
    def add_parser_arguments(cls, add):
        super().add_parser_arguments(add, default_propagation_seconds=900)
        add('credentials', help='netcup credentials INI file.')
        add('login-retries', default=3, type=int,
            help="login retry attempts in case of session timeout")

    def more_info(self):
        return ('This plugin configures a DNS TXT record to respond to a '
                'dns-01 challenge using the netcup API.')

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'netcup credentials INI file',
            {
                'customer-id':  'Customer ID associated with netcup account',
                'api-key':      'Key for CCP API, see {}'.format(API_URL),
                'api-password': 'Password for CCP API, see {}'.format(API_URL),
            }
        )

    def _perform(self, domain, validation_name, validation):
        LOGGER.debug("add_dns_record (%s, %s)", domain, validation_name)
        client = self._get_netcup_client()
        self._determine_zone(domain, lambda domain: (
            client.add_dns_record(domain, validation_name, validation)))

    def _cleanup(self, domain, validation_name, validation):
        LOGGER.debug("delete_dns_record(%s, %s)", domain, validation_name)
        client = self._get_netcup_client()
        self._determine_zone(domain, lambda domain: (
            client.delete_dns_record(domain, validation_name, validation)))

    def _determine_zone(self, domain, func):
        """Find the domain_id for a given domain."""
        domain_name_guesses = dns_common.base_domain_name_guesses(domain)

        for domain_name in domain_name_guesses:
            try:
                return func(domain_name)
            except NetcupZoneError:
                pass

        raise PluginError(
            'Unable to determine zone identifier for {0} using zone names: {1}'
            .format(domain, domain_name_guesses))

    def _get_netcup_client(self):
        credentials = self.credentials.conf
        return APIClient(
            credentials('customer-id'),
            credentials('api-key'),
            credentials('api-password'),
            self.conf('login-retries'))


class APIClient:

    def __init__(self, customer_id, api_key, api_password, login_retries):
        self._customer_id = customer_id
        self._api_key = api_key
        self._api_password = api_password
        self._api_session_id = None
        self._login_retries = login_retries
        if login_retries < 0:
            raise PluginError((
                "Invalid value for --dns-netcup-login-retries: {}. "
                "Must be >= 0."
            ).format(login_retries))

    # public interface

    def add_dns_record(self, domain, name, content):
        """Create record. If it already exists, do nothing."""
        record = _make_record(domain, name, content)
        if not self._query_records(domain, record):
            self._update_records(domain, [record])

    def delete_dns_record(self, domain, name, content):
        """Delete an existing record. If record does not exist, do nothing."""
        # Note that id/type/hostname/destination are all mandatory when
        # deleting. We must query first to retrieve the record id.
        record = _make_record(domain, name, content)
        queried_records = self._query_records(domain, record)
        self._update_records(domain, [
            dict(record_with_id, deleterecord=True)
            for record_with_id in queried_records
        ])

    # internal helpers

    def _query_records(self, domain, record):
        """Query list of record using netcup API."""
        responsedata = self._authenticate_and_call(
            "infoDnsRecords",
            domainname=domain)
        dnsrecords = responsedata.get("dnsrecords", [])
        return [
            retrieved_record
            for retrieved_record in dnsrecords
            if all(retrieved_record[k] == record[k] for k in record)
        ]

    def _update_records(self, domain, records):
        """Insert or update a list of DNS records.

        The fields ``hostname``, ``type``, and ``destination`` are mandatory.
        The field ``id`` is mandatory when ``deleterecord=True``
        """
        return self._authenticate_and_call(
            "updateDnsRecords",
            domainname=domain,
            dnsrecordset={"dnsrecords": records})

    def _authenticate(self, force=False):
        """Authenticate with netcup server. Must be called first."""

        if force or not self._api_session_id:
            responsedata = _apicall("login", {
                "customernumber": self._customer_id,
                "apikey": self._api_key,
                "apipassword": self._api_password,
            })

            self._api_session_id = responsedata.get("apisessionid")
            if not self._api_session_id:
                raise PluginError("Login failed due to unknown reason.")

        return {
            "customernumber": self._customer_id,
            "apikey": self._api_key,
            "apisessionid": self._api_session_id,
        }

    def _authenticate_and_call(self, action, domainname, **param):
        """Authenticate and then perform API call.
        Auto retry login if session timed out."""
        param = dict(param, domainname=domainname)
        session_auth = self._authenticate(False)

        for i in range(self._login_retries):
            try:
                return _apicall(action, session_auth, **param)
            except NetcupSessionTimeoutError:
                LOGGER.info(
                    "Login session timed out during call %s for domain %s. "
                    "Retrying login (attempt %d)",
                    action, domainname, i + 1)
                session_auth = self._authenticate(True)

        return _apicall(action, session_auth, **param)


def _make_record(domain, name, content):
    name = name.removesuffix('.' + domain)
    return {
        "type": "TXT",
        "hostname": name,
        "destination": content,
    }


def _apicall(action, credentials, **param):
    """Call an API method and return response data. For more info, see:
    https://ccp.netcup.net/run/webservice/servers/endpoint"""

    LOGGER.debug("_apicall: %s(%s)", action, param.get('domainname', ''))

    data = {
        "action": action,
        "param": dict(param, **credentials),
    }
    response = requests.post(
        API_ENDPOINT,
        data=json.dumps(data),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
    response.raise_for_status()
    data = response.json()

    status = data.get("status")
    statuscode = data.get("statuscode")
    shortmessage = data.get("shortmessage")
    longmessage = data.get("longmessage")

    if status == "success":     # statuscode == 2000
        return data.get("responsedata", {})

    # This happens when the domain is not chosen properly. Full message is:
    # "Value in field domainname does not match requirements of type: domainname"
    if 'Value in field domainname does not match requirements' in longmessage:
        raise NetcupZoneError(
            action, statuscode, shortmessage, longmessage)

    # The session times out after roughly 30s and fails with this error:
    if 'The session id is not in a valid format.' in longmessage:
        raise NetcupSessionTimeoutError(
            action, statuscode, shortmessage, longmessage)

    # When something with the JSON format was incorrect, there is also:
    # "Api key missing. JSON decode failed while validating request."

    raise NetcupError(
        action, statuscode, shortmessage, longmessage)


class NetcupError(PluginError):

    def __init__(self, action, statuscode, shortmessage, longmessage):
        super().__init__(self._format(
            action, statuscode, shortmessage, longmessage))
        self.action = action
        self.statuscode = statuscode
        self.shortmessage = shortmessage
        self.longmessage = longmessage

    @classmethod
    def _format(cls, action, statuscode, shortmessage, longmessage):
        return (f'{cls.__name__} during {action}: '
                f'{shortmessage} ({statuscode}) {longmessage}')


class NetcupZoneError(NetcupError):
    pass


class NetcupSessionTimeoutError(NetcupError):
    pass
