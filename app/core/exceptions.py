"""全局业务异常定义。"""


class AuthError(Exception):
    """鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。
    
    故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。
    """

    def __init__(self, message: str = "认证失败") -> None:
        super().__init__(message)
        self.message = message


class CryptoError(Exception):
    """加解密失败时抛出：密文被篡改、密钥不匹配或格式非法。"""

    def __init__(self, message: str = "加解密失败") -> None:
        super().__init__(message)
        self.message = message


class ConfigError(Exception):
    """业务配置缺失时抛出：如用户尚未配置 AI Key。"""

    def __init__(self, message: str = "配置缺失") -> None:
        super().__init__(message)
        self.message = message


class AiCallError(Exception):
    """AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。"""

    def __init__(self, message: str = "AI 调用失败") -> None:
        super().__init__(message)
        self.message = message


class AiParseError(Exception):
    """AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。"""

    def __init__(self, message: str = "AI 返回内容解析失败") -> None:
        super().__init__(message)
        self.message = message
