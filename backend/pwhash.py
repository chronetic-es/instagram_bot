import bcrypt
print(bcrypt.hashpw(b'abc123.', bcrypt.gensalt()).decode())