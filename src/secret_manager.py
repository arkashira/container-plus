import json
from dataclasses import dataclass
from typing import Dict

@dataclass
class Secret:
    name: str
    value: str
    encrypted: bool = False

class SecretManager:
    def __init__(self):
        self.secrets = {}
        self.access_control = {}

    def add_secret(self, secret: Secret):
        self.secrets[secret.name] = secret

    def encrypt_secret(self, secret_name: str):
        if secret_name in self.secrets:
            self.secrets[secret_name].encrypted = True
            self.secrets[secret_name].value = self._encrypt(self.secrets[secret_name].value)
        else:
            raise ValueError("Secret not found")

    def decrypt_secret(self, secret_name: str):
        if secret_name in self.secrets:
            if self.secrets[secret_name].encrypted:
                self.secrets[secret_name].value = self._decrypt(self.secrets[secret_name].value)
                self.secrets[secret_name].encrypted = False
            else:
                raise ValueError("Secret is not encrypted")
        else:
            raise ValueError("Secret not found")

    def add_access_control(self, secret_name: str, access_level: str):
        self.access_control[secret_name] = access_level

    def get_secret(self, secret_name: str, access_level: str):
        if secret_name in self.secrets:
            if secret_name in self.access_control:
                if self.access_control[secret_name] == access_level:
                    return self.secrets[secret_name].value
                else:
                    raise ValueError("Access denied")
            else:
                raise ValueError("Access control not set")
        else:
            raise ValueError("Secret not found")

    def _encrypt(self, value: str):
        return json.dumps({"encrypted": True, "value": value})

    def _decrypt(self, value: str):
        return json.loads(value)["value"]
