"""全局业务异常定义。"""


class AuthError(Exception):
    """鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。
    
    故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。
    """

    def __init__(self, message: str = "认证失败") -> None:
        super().__init__(message)
        self.message = message
