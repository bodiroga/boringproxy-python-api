#!/usr/bin/env python3

from bs4 import BeautifulSoup
import logging
import random
import re
import requests
import string

logger = logging.getLogger(__name__)


class BoringproxyBaseAPI:

    def __init__(self, server_host, access_token):
        self.server_host = server_host
        self.access_token = access_token
        self.headers = {"Authorization": "Bearer " + self.access_token}
        self.users_endpoint = f"https://{self.server_host}/users"
        self.delete_user_endpoint = f"https://{self.server_host}/delete-user"
        self.tokens_endpoint = f"https://{self.server_host}/tokens"
        self.clients_endpoint = f"https://{self.server_host}/clients"
        self.delete_client_endpoint = f"https://{self.server_host}/delete-client"
        self.tunnels_endpoint = f"https://{self.server_host}/tunnels"
        self.delete_tunnel_endpoint = f"https://{self.server_host}/delete-tunnel"


class BoringproxyAdminAPI(BoringproxyBaseAPI):

    def __init__(self, server_host, access_token):
        super().__init__(server_host, access_token)
        self.registered_users = self.get_users()

    def get_users(self):
        r = requests.get(self.users_endpoint, headers=self.headers)
        if not r.status_code == 200:
            return
        soup = BeautifulSoup(r.content, "html.parser")
        user_divs = soup.find_all("div", class_="list-item")

        return [user.get_text().replace("\n", "").replace("Delete", "").strip()
                for user in user_divs]

    def create_user(self, username):
        if len(username) < 6:
            logger.error(f"Username must be at least 6 charaters: {username}")
            return
        if username in self.registered_users:
            logger.warning(f"User '{username}' already registered")
            return
        payload = {"username": username}
        r = requests.post(self.users_endpoint,
                          headers=self.headers, data=payload)
        if not r.status_code == 200:
            logger.error(f"User '{username}' could not be created")
            return
        self.registered_users = self.get_users()
        return True

    def delete_user(self, username):
        if not username in self.registered_users:
            logger.warning(f"Client '{username}' is not registered")
            return
        endpoint = f"{self.delete_user_endpoint}?username={username}"
        payload = {"username": username}
        r = requests.get(endpoint,
                         headers=self.headers, data=payload)
        return r.status_code == 200

    def check_user(self, username):
        return username in self.registered_users

    def create_full_user(self, username):
        exists = self.check_user(username)
        if not exists:
            self.create_user(username)
        else:
            logger.warning(f"Warning: User '{username}' already exists")

        user_token = self.get_user_token(username)
        if user_token:
            logger.warning(f"Warning: token for '{username}' already exists")
            return
        self.create_token(username)

    def get_users_tokens(self):
        r = requests.get(self.tokens_endpoint, headers=self.headers)
        soup = BeautifulSoup(r.content, "html.parser")

        token_spans = soup.find_all("span", class_="token")
        token_texts = [token.get_text() for token in token_spans]

        regex = r"(?P<token>.*) \(Owner: (?P<owner>.*)\) \(Client: (?P<client>.*)\)"
        tokens = {}
        for token_text in token_texts:
            matches = re.search(regex, token_text)
            if not matches:
                continue
            token = matches.group("token")
            user = matches.group("owner")
            if user in tokens:
                logger.warning(f"Warning: token for '{user}' already exist")
            else:
                tokens[user] = token

        return tokens

    def create_token(self, username, client="any"):
        payload = {"owner": username, "client": client}
        r = requests.post(self.tokens_endpoint,
                          headers=self.headers, data=payload)
        return r.status_code == 200

    def get_user_token(self, username):
        tokens = self.get_users_tokens()
        return tokens.get(username)


class BoringproxyUserAPI(BoringproxyBaseAPI):

    def __init__(self, server_host, user_name, access_token):
        super().__init__(server_host, access_token)
        self.user_name = user_name
        self.registered_clients = self.get_clients()

    def get_clients(self):
        r = requests.get(self.clients_endpoint, headers=self.headers)
        soup = BeautifulSoup(r.content, "html.parser")
        client_spans = soup.find_all("span", class_="client")

        return [client.get_text().replace(f" (Owner: {self.user_name})", "").strip()
                for client in client_spans]

    def create_client(self, name):
        if not name in self.registered_clients:
            payload = {"owner": self.user_name, "client-name": name}
            r = requests.post(self.clients_endpoint,
                              headers=self.headers, data=payload)
            if not r.status_code == 200:
                logger.error(f"Client '{name}' could not be created")
                return
            self.registered_clients = self.get_clients()
        client = BoringproxyClientAPI(self, name)
        return client

    def delete_client(self, name):
        if not name in self.registered_clients:
            logger.warning(f"Client '{name}' is not registered")
            return
        endpoint = f"{self.delete_client_endpoint}?owner={self.user_name}&client-name={name}"
        payload = {"owner": self.user_name, "client-name": name}
        r = requests.get(endpoint,
                         headers=self.headers, data=payload)
        return r.status_code == 200


class BoringproxyClientAPI:

    def __init__(self, user, name):
        self.user = user
        self.name = name
        self.registered_tunnels = {}

    def create_tunnel(self, port):
        subdomain = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=15))
        domain = f"{subdomain}.{self.user.server_host}"
        if self.__create_tunnel(domain, port):
            self.registered_tunnels[port] = domain

    def delete_tunnel(self, port):
        if not port in self.registered_tunnels:
            logger.warning(f"Tunnel for port '{port}' is not running")
            return
        domain = self.registered_tunnels[port]
        endpoint = f"{self.user.delete_tunnel_endpoint}?domain={domain}"
        payload = {"domain": domain}
        r = requests.get(endpoint, headers=self.user.headers, data=payload)
        return r.status_code == 200

    def __create_tunnel(self, domain, client_port, tunnel_port="Random", client_addr="127.0.0.1", tls_termination="client-tls", username=None, password=None):
        owner = self.user.user_name
        client_name = self.name

        payload = {"domain": domain, "owner": owner, "tunnel-port": tunnel_port, "client-name": client_name, "client-addr": client_addr,
                   "client-port": client_port, "tls-termination": tls_termination}  # "username": username, "password": password}
        r = requests.post(self.user.tunnels_endpoint,
                          headers=self.user.headers, data=payload)
        return r.status_code == 200
