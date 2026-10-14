"""
This module defines a certbot plugin to automate the process of completing a
``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and subsequently
removing, TXT records using the netcup CCP API or netcup DNS API.
"""

# Keep metadata before any imports (for setup.py)!
__version__ = '2.0.3'
__url__     = 'https://github.com/coldfix/certbot-dns-netcup'
__all__     = ['Authenticator']

import json
import logging
import requests
from urllib.parse import quote

from certbot.plugins import dns_common
from certbot.errors import PluginError


V0_API_URL = "https://www.netcup.com/en/helpcenter/documentation/domain/our-api"
V1_API_URL = "https://www.netcup.com/en/helpcenter/documentation/general/netcup-api"

V0_API_ENDPOINT = "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"
V1_API_ENDPOINT = "https://api.netcup.com"

ACME_PREFIX = "_acme-challenge"

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
        self._v0_client = None
        self._v1_client = None

    # DNSAuthenticator overrides

    @classmethod
    def add_parser_arguments(cls, add):
        super().add_parser_arguments(add, default_propagation_seconds=900)
        add('credentials', help='netcup credentials INI file.')
        add('login-retries', default=3, type=int,
            help="login retry attempts in case of session timeout")
        add('zone-name', help=(
            "zone name to operate on (often second-level-domain). "
            "Will be determined using brute-force requests if not specified."))

    def more_info(self):
        return ('This plugin configures a DNS TXT record to respond to a '
                'dns-01 challenge using the netcup API.')

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'netcup credentials INI file',
            {})
        # These variables are currently optional because either new or old
        # API can be used. When we drop support for the legacy API, the
        # new API key can be made mandatory again.
        #
        # 'customer-id':  'Customer ID associated with netcup account',
        # 'api-key':      'Key for (legacy) CCP API, see {}'.format(V0_API_URL),
        # 'api-password': 'Password for CCP API, see {}'.format(V0_API_URL),
        # 'api-v1-key':   'Key for netcup API v1, see {}'.format(V1_API_URL),

    def _perform(self, domain, validation_name, validation):
        LOGGER.debug("add_dns_record (%s, %s)", domain, validation_name)
        self._determine_zone(domain, lambda client, domain: (
            client.add_dns_record(domain, validation_name, validation)))

    def _cleanup(self, domain, validation_name, validation):
        LOGGER.debug("delete_dns_record(%s, %s)", domain, validation_name)
        self._determine_zone(domain, lambda client, domain: (
            client.delete_dns_record(domain, validation_name, validation)))

    def _determine_zone(self, domain, func):
        """Find the domain_id for a given domain."""
        self._create_clients()

        zone_name = self.conf('zone-name')
        if zone_name:
            if self._v1_client:
                try:
                    return func(self._v1_client, zone_name)
                except NetcupZoneError:
                    # In my trials all legacy domains are listed with the new
                    # API as well. This would mean that the v0_client will not
                    # do better here. But let's give this finding the benefit
                    # of the doubt and try anyway if v0_client is available:
                    if not self._v0_client:
                        raise
                except NetcupUnmanagedDomainError as e:
                    # This exception means zone is managed by legacy API.
                    # Credentials for legacy API are required.
                    if not self._v0_client:
                        raise PluginError(
                            "Domain is not managed by new API, "
                            "but credentials for legacy API are missing."
                        ) from e

            return func(self._v0_client, zone_name)

        domain_name_guesses = dns_common.base_domain_name_guesses(domain)

        if self._v1_client:
            for domain_name in domain_name_guesses:
                try:
                    return func(self._v1_client, domain_name)
                except NetcupZoneError:
                    pass
                except NetcupUnmanagedDomainError as e:
                    # Domain was found but is handled by legacy API:
                    if self._v0_client:
                        return func(self._v0_client, domain_name)
                    else:
                        raise PluginError(
                            "Domain is not managed by new API, "
                            "but credentials for legacy API are missing."
                        ) from e

        if self._v0_client:
            for domain_name in domain_name_guesses:
                try:
                    return func(self._v0_client, domain_name)
                except NetcupZoneError:
                    pass

        raise PluginError(
            'Unable to determine zone identifier for {0} using zone names: {1}'
            .format(domain, domain_name_guesses))

    def _create_clients(self):
        if not (self._v0_client or self._v1_client):
            self._v0_client = self._create_v0_client()
            self._v1_client = self._create_v1_client()
        if not (self._v0_client or self._v1_client):
            raise PluginError("No credentials were specified!")

    def _create_v0_client(self):
        v0_cred = (
            self.credentials.conf('customer-id'),
            self.credentials.conf('api-key'),
            self.credentials.conf('api-password'))

        if any(v0_cred) and not all(v0_cred):
            raise PluginError((
                "Credentials for legacy API partially missing! "
                "You must specify either all or none of:\n"
                " - customer-id  ({})\n"
                " - api-key      ({})\n"
                " - api-password ({})\n"
            ).format(*[
                'specified' if value else 'missing'
                for value in v0_cred
            ]))

        if all(v0_cred):
            LOGGER.debug("Creating v0 API client.")
            return APIClientV0(*v0_cred, self.conf('login-retries'))

    def _create_v1_client(self):
        api_key = self.credentials.conf('api-v1-key')
        if api_key:
            LOGGER.debug("Creating v1 API client.")
            return APIClientV1(api_key)


class APIClientV0:

    """
    API client for the legacy API, see:

    https://ccp.netcup.net/run/webservice/servers/endpoint.php

    API usage / dynamic behaviour:

        add_dns_record:
        - login()               login every time to avoid session timeout
        - updateDnsRecords()    insert the new record

        delete_dns_record
        - login()               login every time to avoid session timeout
        - infoDnsRecords()      retrieve existing record (needed for deletion)
        - updateDnsRecords()    delete given record
    """

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
        """Create record."""
        record = _make_record(domain, name, content)
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
                LOGGER.warning(
                    "Login session timed out during call %s for domain %s. "
                    "Retrying login (attempt %d)",
                    action, domainname, i + 1)
                session_auth = self._authenticate(True)

        return _apicall(action, session_auth, **param)


class APIClientV1:

    """
    API client for the v1 API (CloudDNS), see:

    https://www.netcup.com/en/helpcenter/documentation/netcup-api

    API usage / dynamic behaviour:

        add_dns_record:
        - GET       /v1/domain?fqdn=...
        - POST      /v1/domain/{id}/acme/challenge

        delete_dns_record:
        - GET       /v1/domain?fqdn=...
        - DELETE    /v1/domain/{id}/acme/challenge/{scope}/{value}
    """

    def __init__(self, api_key):
        self._api_key = api_key
        self._domains = self._query_domains()

    def add_dns_record(self, domain, name, value):
        """Create record."""
        scope = _get_scope(domain, name)
        domain_id = self._get_domain(domain)["id"]
        self._apicall("POST", f"v1/domain/{domain_id}/acme/challenge", json={
            "scope": scope,
            "value": value,
        })

    def delete_dns_record(self, domain, name, value):
        """Delete an existing record. If record does not exist, do nothing."""
        value = quote(value)
        scope = quote(_get_scope(domain, name), safe="@")
        domain_id = self._get_domain(domain)["id"]
        self._apicall("DELETE", f"/v1/domain/{domain_id}/acme/challenge/{scope}/{value}")

    def _query_domains(self):
        domains = {}
        page = 1
        while True:
            response = self._apicall("GET", "v1/domain", params={page: page})
            data = response.json()

            for domain_entry in data["result"]:
                domains[domain_entry["fqdn"].rstrip(".")] = domain_entry

            if page == data["meta"]["pagination"]["lastPage"]:
                return domains
            page += 1

    def _get_domain(self, domain):
        LOGGER.debug("API v1: get domain %s", domain)
        try:
            domain = self._domains[domain.rstrip(".")]
        except KeyError:
            code = "ResourceNotFound"
            message = "Domain is not a valid zone."
            raise NetcupZoneError("queryDomain", 400, code, message)

        if not domain["isDnsManaged"]:
            code = "UnmanagedDomain"
            message = "Domain is not managed by v1 API."
            raise NetcupUnmanagedDomainError("queryDomain", 404, code, message)

        return domain

    def _apicall(self, method, resource, **kwargs):
        LOGGER.debug("API v1: %s /%s", method, resource)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        response = requests.request(
            method,
            f"{V1_API_ENDPOINT}/{resource}",
            headers=headers,
            **kwargs)
        data = response.json()
        if data["success"]:
            return response

        status = response.status_code
        action = f"{method} /{resource}"

        for error in data["errors"]:
            code = error.get("code", "Unknown")
            message = error.get("message", "Unknown error")
            # Known errors:
            # 400 authenticationError: Authentication token is not valid or has expired.
            # 404 resourceDoesNotExist: No results found, the page number may be too high.
            if (
                status == 404
                or code == "resourceDoesNotExist"
                or message == "No results found, the page number may be too high."
            ):
                raise NetcupZoneError(action, status, code, message)

            raise NetcupError(action, status, code, message)

        raise NetcupError(action, status, "Unknown", "Unknown")


def _make_record(domain, name, content):
    name = name.removesuffix('.' + domain)
    return {
        "type": "TXT",
        "hostname": name,
        "destination": content,
    }


def _get_scope(domain, name):
    name = name.rstrip(".")
    scope = name.removesuffix("." + domain.rstrip("."))
    if scope == ACME_PREFIX:
        return "@"
    if not scope.startswith(ACME_PREFIX + "."):
        raise PluginError((
            "Expecting validation name to start with `{}.*`. "
            "Got: {}"
        ).format(ACME_PREFIX, name))
    return scope.removeprefix(ACME_PREFIX + ".")


def _apicall(action, credentials, **param):
    """Call an API method and return response data. For more info, see:
    https://ccp.netcup.net/run/webservice/servers/endpoint"""

    LOGGER.debug("API v0: /%s(%s)", action, param.get('domainname', ''))

    data = {
        "action": action,
        "param": dict(param, **credentials),
    }
    response = requests.post(
        V0_API_ENDPOINT,
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
    if (
        statuscode == 4013
        or 'Value in field domainname does not match requirements' in longmessage
    ):
        raise NetcupZoneError(
            action, statuscode, shortmessage, longmessage)

    # The session times out after roughly 30s and fails with this one of the
    # the following error messages. The first one was likely replaced by the
    # second one, but it could change again at any time, so we check for the
    # statuscode as well.
    if (
        statuscode == 4001
        or 'The session id is not in a valid format.' in longmessage
        or 'Api session not found' in longmessage
    ):
        raise NetcupSessionTimeoutError(
            action, statuscode, shortmessage, longmessage)

    # I've also seen:
    # 4013 Validation Error: "More than 180 requests per minute. Please wait
    # and retry later. Please contact our customer service to find out if the
    # limitation of requests can be increased."

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
        LOGGER.debug("%s", self)

    @classmethod
    def _format(cls, action, statuscode, shortmessage, longmessage):
        return (f'{cls.__name__} during {action}: '
                f'{shortmessage} ({statuscode}) {longmessage}')


class NetcupZoneError(NetcupError):
    pass


class NetcupUnmanagedDomainError(NetcupError):
    pass


class NetcupSessionTimeoutError(NetcupError):
    pass
