""" EEN Client Library"""
import json
import logging
import re
import time
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from requests.exceptions import RequestException


class AuthenticationError(Exception):
    pass


class TokenStorage(ABC):
    @abstractmethod
    def get(self, key):
        pass

    @abstractmethod
    def set(self, key, value):
        pass

    @abstractmethod
    def __contains__(self, key):
        pass


class EENClient:
    auth_url = "https://auth.eagleeyenetworks.com/oauth2/authorize"

    def __init__(self, client_id, client_secret, redirect_uri, token_storage, max_retries=3):
        if not isinstance(token_storage, TokenStorage):
            raise TypeError("token_storage must implement the TokenStorage interface.")
        self.client_id = client_id
        self.client_secret = client_secret
        self.max_retries = max_retries
        self.redirect_uri = redirect_uri
        self.token_storage = token_storage
        self.logger = logging.getLogger(__name__)
        self._load_resources()

    def _load_resources(self):
        pass  # Placeholder for loading dynamic resources if required

    def __retry_request(self, request_func, *args, **kwargs):
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                response = request_func(*args, **kwargs)
                if response.ok:
                    return response
                elif response.status_code == 401:
                    self.logger.info("Auth failed. Refreshing Access Token.")
                    self.refresh_access_token()
                else:
                    raise RequestException(f"{response.status_code} Response: {response.text}")
            except (AuthenticationError, RequestException) as e:
                self.logger.error("Request failed: %s. %d/%d", e, retry_count, self.max_retries)
                if retry_count == self.max_retries:
                    raise
                retry_count += 1
                time.sleep(2 ** retry_count)

    def _api_call(self, endpoint, method='GET', params=None, data=None, headers=None, stream=False):
        access_token = self.token_storage.get('access_token')
        base_url = self.token_storage.get('base_url')
        if not base_url:
            raise Exception("Base URL not found in token storage")
        url = f"https://{base_url}/api/v3.0{endpoint}"
        if params:
            url += '?' + urllib.parse.urlencode(params)
        self.logger.info(f"request: {url}")
        if not headers:
            headers = {
                "accept": "application/json",
                "content-type": "application/json"
            }
        headers['Authorization'] = f'Bearer {access_token}'

        def request_func():
            if method == 'GET':
                return requests.get(url, headers=headers, stream=stream)
            elif method == 'POST':
                return requests.post(url, headers=headers, data=json.dumps(data))
            elif method == 'PATCH':
                return requests.patch(url, headers=headers, data=json.dumps(data))
            elif method == 'DELETE':
                return requests.delete(url, headers=headers)
        response = self.__retry_request(request_func)
        if stream:
            return response
        return response


    def get_auth_url(self):
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "vms.all",
            "redirect_uri": self.redirect_uri
        }
        return self.auth_url + '?' + urllib.parse.urlencode(params)

    def auth_een(self, token, type="code"):
        url = "https://auth.eagleeyenetworks.com/oauth2/token"
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code" if type == "code" else "refresh_token",
            "scope": "vms.all",
            "redirect_uri": self.redirect_uri
        }
        if type == "code":
            data["code"] = token
        else:
            data["refresh_token"] = token
        response = requests.post(
            url,
            auth=(self.client_id, self.client_secret),
            data=data,
            headers=headers,
            timeout=10  # 10 seconds timeout
        )
        if response.ok:
            auth_response = response.json()
            self.token_storage.set('access_token', auth_response['access_token'])
            self.token_storage.set('refresh_token', auth_response['refresh_token'])
            self.token_storage.set('base_url', auth_response['httpsBaseUrl']['hostname'])
        else:
            raise AuthenticationError(f"Authentication Failed: {response.status_code} {response.text}")
        return response

    def refresh_access_token(self):
        refresh_token = self.token_storage.get('refresh_token')
        if not refresh_token:
            raise AuthenticationError("No refresh token found.")
        self.auth_een(refresh_token, type="refresh")

    # Utility functions
    def format_timestamp(self, timestamp_str, user_timezone='UTC'):
        if not timestamp_str:
            return None
        try:
            local_dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M')
            local_tz = ZoneInfo(user_timezone)
            local_dt = local_dt.replace(tzinfo=local_tz)
            utc_dt = local_dt.astimezone(ZoneInfo('UTC'))
            return utc_dt.isoformat(timespec='milliseconds')
        except ValueError:
            return None

    def get_timestamps(self):
        current_time = datetime.now(timezone.utc)
        seven_days_ago = current_time - timedelta(days=7)
        current_time_iso = current_time.isoformat(timespec='milliseconds')
        seven_days_ago_iso = seven_days_ago.isoformat(timespec='milliseconds')
        return current_time_iso, seven_days_ago_iso

    def camel_to_title(self, camel_str, acronyms=['pos', 'lpr']):
        title_str = re.sub(r'([a-z])([A-Z])', r'\1 \2', camel_str).title()
        for acronym in acronyms:
            title_str = re.sub(
                fr'\b({acronym})\b',
                acronym.upper(),
                title_str,
                flags=re.IGNORECASE
            )
        return title_str

    # Role-related methods
    def get_roles(self, include=None):
        params = {}
        if include:
            params['include'] = ','.join(include)
        return self._api_call("/roles", "GET", params=params)

    def create_role(self, body):
        return self._api_call("/roles", "POST", data=body)

    def delete_role(self, role_id):
        return self._api_call(f"/roles/{role_id}", "DELETE")

    def get_role(self, role_id, include=None):
        params = {}
        if include:
            params['include'] = ','.join(include)
        return self._api_call(f"/roles/{role_id}", "GET", params=params)

    def update_role(self, role_id, body):
        return self._api_call(
            f"/roles/{role_id}", "PATCH", data=body
        )

    # Role Assignments
    def get_role_assignments(self, roleId__in=None):
        params = {}
        if roleId__in:
            params['roleId__in'] = ','.join(roleId__in)
        return self._api_call("/roleAssignments", "GET", params=params)

    def create_role_assignments(self, body):
        return self._api_call("/roleAssignments:bulkcreate", method='POST', data=body)

    def delete_role_assignments(self, body):
        return self._api_call("/roleAssignments:bulkdelete", method='POST', data=body)

    # User-related methods
    def get_users(self, include=None):
        params = {}
        if include:
            params['include'] = ','.join(include)
        return self._api_call("/users", "GET", params=params)

    def create_user(self, body):
        return self._api_call("/users", "POST", data=body )

    def get_user(self, user_id, include=None):
        params = {}
        if include:
            params['include'] = ','.join(include)
        return self._api_call(f"/users/{user_id}", "GET", params=params )

    def delete_user(self, user_id):
        return self._api_call(f"/users/{user_id}", "DELETE")

    def update_user(self, user_id, body):
        return self._api_call(f"/users/{user_id}", "PATCH", data=body)

    def get_current_user(self, include=None):
        params = {}
        if include:
            params['include'] = ','.join(include)
        return self._api_call("/users/self", "GET", params=params)

    def update_current_user(self, body):
        return self._api_call("/users/self", "PATCH",data=body)

    def get_trusted_clients(self, include=None):
        params = {}
        if include:
            params['include'] = ','.join(include)
        return self._api_call("/users/self/trustedClients", "GET", params=params)

    def delete_trusted_client(self, trusted_client_id):
        return self._api_call(f"/users/self/trustedClients/{trusted_client_id}", "DELETE")

    def get_preference(self, preference_id):
        return self._api_call(f"/users/self/preferences/{preference_id}", "GET")

    def update_preference(self, preference_id, body):
        return self._api_call(f"/users/self/preferences/{preference_id}", "PATCH", data=body)

    def delete_preference(self, preference_id):
        return self._api_call(f"/users/self/preferences/{preference_id}", "DELETE")
