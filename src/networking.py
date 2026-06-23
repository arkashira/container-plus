import json
from dataclasses import dataclass
from enum import Enum
from typing import List

class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"

@dataclass
class NetworkingConfig:
    protocol: Protocol
    port: int
    ip_address: str

class Networking:
    def __init__(self):
        self.configs = []

    def configure(self, protocol: Protocol, port: int, ip_address: str):
        config = NetworkingConfig(protocol, port, ip_address)
        self.configs.append(config)
        return config

    def get_config(self, protocol: Protocol):
        for config in self.configs:
            if config.protocol == protocol:
                return config
        return None

    def update_config(self, protocol: Protocol, port: int, ip_address: str):
        config = self.get_config(protocol)
        if config:
            config.port = port
            config.ip_address = ip_address
            return config
        return None

    def delete_config(self, protocol: Protocol):
        self.configs = [config for config in self.configs if config.protocol != protocol]

    def get_real_time_feedback(self, protocol: Protocol):
        config = self.get_config(protocol)
        if config:
            return json.dumps({
                "protocol": config.protocol.value,
                "port": config.port,
                "ip_address": config.ip_address
            })
        return None
