from django.db import models


class FwUserInfo:
    def __init__(self) -> None:
        self.first_name = ''
        self.last_name = ''

class FwContextInfo:
    def __init__(self) -> None:
        self.user = FwUserInfo()
        self.projects = []
        self.current_path = 'wandell/'