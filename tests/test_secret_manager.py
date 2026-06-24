from secret_manager import Secret, SecretManager

def test_add_secret():
    manager = SecretManager()
    secret = Secret("test", "value")
    manager.add_secret(secret)
    assert manager.secrets["test"].value == "value"

def test_encrypt_secret():
    manager = SecretManager()
    secret = Secret("test", "value")
    manager.add_secret(secret)
    manager.encrypt_secret("test")
    assert manager.secrets["test"].encrypted
    assert manager.secrets["test"].value != "value"

def test_decrypt_secret():
    manager = SecretManager()
    secret = Secret("test", "value")
    manager.add_secret(secret)
    manager.encrypt_secret("test")
    manager.decrypt_secret("test")
    assert not manager.secrets["test"].encrypted
    assert manager.secrets["test"].value == "value"

def test_add_access_control():
    manager = SecretManager()
    secret = Secret("test", "value")
    manager.add_secret(secret)
    manager.add_access_control("test", "admin")
    assert manager.access_control["test"] == "admin"

def test_get_secret():
    manager = SecretManager()
    secret = Secret("test", "value")
    manager.add_secret(secret)
    manager.add_access_control("test", "admin")
    assert manager.get_secret("test", "admin") == "value"

def test_get_secret_access_denied():
    manager = SecretManager()
    secret = Secret("test", "value")
    manager.add_secret(secret)
    manager.add_access_control("test", "admin")
    try:
        manager.get_secret("test", "user")
        assert False
    except ValueError as e:
        assert str(e) == "Access denied"

def test_get_secret_not_found():
    manager = SecretManager()
    try:
        manager.get_secret("test", "admin")
        assert False
    except ValueError as e:
        assert str(e) == "Secret not found"
