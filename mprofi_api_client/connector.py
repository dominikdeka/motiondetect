# -*- coding: utf-8 -*-
"""Module with connector managing communication with Mprofi API."""

import os

from .packages.requests import Session
from .packages.requests.compat import json
from .packages.requests.exceptions import ConnectionError, HTTPError


class MprofiConnectionError(Exception):
    pass


class MprofiAuthError(Exception):
    pass


class MprofiNotFoundError(Exception):
    pass


class MprofiAPIConnector(object):

    """Connector class that manages communication  with mprofi public API.

    :param api_token: Optional, explicit api token, as string. If api_token
        is not specified `MPROFI_API_TOKEN` env variable will be used.
    :param payload: Optional initial payload (list of dicts).

    :Example:

    >>> connector = MprofiAPIConnector(api_token="token from mprofi.pl website")
    >>> connector.add_message('111222333', 'Welcome!')
    >>> connector.send()
    ... {u'id': 1}  # This will be a dict with message id

    Sending multiple messages will change `send()` results

    >>> connector = MprofiAPIConnector(api_token="token from mprofi.pl website")
    >>> connector.add_message('111222333', 'Welcome!')
    >>> connector.add_message('111222333', 'Welcome!')
    >>> connector.send()
    ... {u'result': [{u'id': 2}, {u'id': 3}]}  # a dict with results in a list
    >>> # now `response` property has all added messages with ids
    >>> connector.response
    ... [
    ...     {
    ...         u'id': 2,
    ...         'message': 'Hello!',
    ...         'recipient': '123123123'
    ...     },
    ...     {
    ...         u'id': 3,
    ...         'message': 'Hello!',
    ...         'recipient': '123123123'
    ...     }
    ... ]
    >>> # you can also grab current status of messages you've sent
    >>> connector.get_status()
    ... [
    ...     {
    ...         u'id': 2,
    ...         u'reference': u'2015-02-05',  # you can set own reference
    ...                                       # string as `send()` argument
    ...         u'status': u'WAITING_TO_PROCESS',
    ...         u'ts': None
    ...     },
    ...     {
    ...         u'id': 3,
    ...         u'reference': u'2015-02-05',
    ...         u'status': u'WAITING_TO_PROCESS',
    ...         u'ts': None
    ...     }
    ... ]
    >>> # or you can request status of specified message ids
    >>> connector.get_status(requested_ids=['1', '2'])
    ... [
    ...     {
    ...         u'id': 1,
    ...         u'reference': u'2015-02-05',  # you can set own reference
    ...                                       # string as `send()` argument
    ...         u'status': u'ERROR',
    ...         u'ts': None
    ...     },
    ...     {
    ...         u'id': 2,
    ...         u'reference': u'2015-02-05',
    ...         u'status': u'PROCESSING',
    ...         u'ts': None
    ...     }
    ... ]

    """

    #: Base URL for public API
    url_base = 'https://api.mprofi.pl'

    #: Version of API stored as string (used to merge with url_base)
    api_version = '1.0'

    #: Name of send endpoint
    send_endpoint = 'send'

    #: Name of bulk send endpoint
    sendbulk_endpoint = 'sendbulk'

    #: Name of status endpoint
    status_endpoint = 'status'

    def __init__(self, api_token=None, payload=None):
        self.token = api_token or os.environ.get('MPROFI_API_TOKEN', '')
        self.session = Session()
        self.session.headers.update({
            'Authorization': 'Token {0}'.format(self.token)
        })
        self.payload = payload or []
        self.response = []

    def add_message(self, recipient, message):
        """Add one message to current payload.

        :param recipient: Message recipient as string. This should be telephone
            number like `123 123 123`.
        :param message: Message content as string.

        :raises: ValueError
        :returns: None

        """

        if not recipient:
            raise ValueError("`recipient` can't be empty.")
        if not message:
            raise ValueError("`message` can't be empty.")

        self.payload.append({
            'recipient': recipient,
            'message': message
        })

    def send(self, reference=None):
        """Send message or messages stored in payload.

        :param reference: Optional string that will be stored in mprofi to
            mark messages from this batch.

        This method will use different endpoints of api (send or sendbulk)
        depending on the size of payload. When sending only one message -
        `send` api endpoint will be used, when sending multiple messages -
        it will use `sendbulk` endpoint.

        :raises: ValueError, MprofiConnectionError, MprofiAuthError
        :returns: JSON string with updated status data

        """

        if len(self.payload) == 1:
            used_endpoint = self.send_endpoint
            full_payload = self.payload[0]
            if reference is not None:
                full_payload.update({
                    'reference': reference
                })
            extract_from_response = lambda r: [{'id': r['id']}]

        elif len(self.payload) > 1:
            used_endpoint = self.sendbulk_endpoint
            full_payload = {
                'messages': self.payload
            }
            if reference is not None:
                full_payload.update({
                    'reference': reference
                })
            extract_from_response = lambda r: r['result']

        else:
            raise ValueError("Empty payload. Please use `add_message` first.")

        full_url = '/'.join([
            self.url_base,
            self.api_version,
            used_endpoint, ""
        ])

        try:
            response = self.session.post(
                full_url,
                data=full_payload,
                verify=True
            )
            response.raise_for_status()
        except ConnectionError:
            raise MprofiConnectionError(
                "Can't reach %s, please check internet"
                " connection." % self.url_base
            )
        except HTTPError:
            raise MprofiAuthError(
                "Calling %s resulted in an error. "
                "Did you set proper, active, token?" % self.url_base
            )

        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise MprofiConnectionError(
                "Can't reach %s, please check internet"
                " connection." % self.url_base
            )

        self.response = self.payload
        self.payload = []

        for sent_message, response_message in zip(
                self.response,
                extract_from_response(response_json)
        ):
            sent_message.update(response_message)

        return response_json

    def get_status(self, requested_ids=None):
        """Check status of messages existing in payload or with given ids.

        If you don't supply `requested_ids` this method will grab message id
        from each message in payload and call to API to check message status.
        When list of `requested_ids` is given, method will check message status
        of messages with requested ids.

        :param requested_ids: Optional list of requested message ids (if you
            don't want to check for last send messages).

        :raises: MprofiConnectionError, MprofiNotFoundError, MprofiAuthError
        :returns: JSON string with updated status data

        """
        status_full_url = '/'.join([
            self.url_base,
            self.api_version,
            self.status_endpoint, ""
        ])

        collected_response = {}

        if requested_ids is None:
            requested_ids = [sent_msg['id'] for sent_msg in self.response]

        for message_id in requested_ids:

            try:
                response = self.session.get(
                    status_full_url,
                    params={'id': message_id},
                    verify=True
                )
                response.raise_for_status()
            except ConnectionError:
                raise MprofiConnectionError(
                    "Can't reach %s, please check internet"
                    " connection." % self.url_base
                )
            except HTTPError:
                if response.status_code != 404:
                    raise MprofiAuthError(
                        "Calling %s resulted in an error. "
                        "Did you set proper, active, token?" % self.url_base
                    )
                else:
                    raise MprofiNotFoundError(
                        "We can't find a message with id %s" % message_id
                    )

            try:
                collected_response[message_id] = response.json()
            except json.JSONDecodeError:
                raise MprofiConnectionError(
                    "Can't reach %s, please check internet"
                    " connection." % self.url_base
                )

        return collected_response
