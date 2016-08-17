import jwt
import config


class JwtToken:
    
    def __init__(self):
        self.secret = config.JWT_TOKEN_SECRET
        self.algorithm = 'HS256'

    def generate(self, data):
        return jwt.encode(data, self.secret, self.algorithm)

    def validate(self, token):
        try:
            return jwt.decode(token, self.secret, self.algorithm)
        except jwt.exceptions.DecodeError:
            return {}
