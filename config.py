from cryptography.fernet import Fernet

data="password"

def encrypt(data):
    key = Fernet.generate_key()
    print(key)
    cipher_suite = Fernet(key)
    with open("data_encrypted", "wb") as file:
        file.write(cipher_suite.encrypt(data.encode()))
        
encrypt(data)