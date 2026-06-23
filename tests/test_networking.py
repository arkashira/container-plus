import json
from networking import Networking, Protocol, NetworkingConfig

def test_configure():
    networking = Networking()
    config = networking.configure(Protocol.TCP, 8080, "192.168.1.1")
    assert config.protocol == Protocol.TCP
    assert config.port == 8080
    assert config.ip_address == "192.168.1.1"

def test_get_config():
    networking = Networking()
    networking.configure(Protocol.TCP, 8080, "192.168.1.1")
    config = networking.get_config(Protocol.TCP)
    assert config.protocol == Protocol.TCP
    assert config.port == 8080
    assert config.ip_address == "192.168.1.1"

def test_update_config():
    networking = Networking()
    networking.configure(Protocol.TCP, 8080, "192.168.1.1")
    config = networking.update_config(Protocol.TCP, 8081, "192.168.1.2")
    assert config.protocol == Protocol.TCP
    assert config.port == 8081
    assert config.ip_address == "192.168.1.2"

def test_delete_config():
    networking = Networking()
    networking.configure(Protocol.TCP, 8080, "192.168.1.1")
    networking.delete_config(Protocol.TCP)
    assert networking.get_config(Protocol.TCP) is None

def test_get_real_time_feedback():
    networking = Networking()
    networking.configure(Protocol.TCP, 8080, "192.168.1.1")
    feedback = networking.get_real_time_feedback(Protocol.TCP)
    assert json.loads(feedback) == {
        "protocol": "tcp",
        "port": 8080,
        "ip_address": "192.168.1.1"
    }

def test_get_real_time_feedback_none():
    networking = Networking()
    feedback = networking.get_real_time_feedback(Protocol.TCP)
    assert feedback is None
