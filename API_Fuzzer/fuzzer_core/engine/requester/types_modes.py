from enum import Enum


class AuthMode(Enum):
    BASIC = "Basic-auth"
    DIGEST = "Digest-auth"
    BEARER = "Bearer-auth"
    APIKEY = "API-key-auth"
    JWT = "JWT-auth"
    OAUTH2 = "OAuth2-auth"
    OAUTH1 = "OAuth1-auth"
    NTLM = "NTLM-auth"
    AWS = "AWS4-auth"
    CUSTOM = "Custom-auth"


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    TRACE = "TRACE"
    CONNECT = "CONNECT"
