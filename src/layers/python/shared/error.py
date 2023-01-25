class NotFoundException(Exception):
    pass

class GateKeeperException(Exception):
    def __init__(self, code, message="GateKeeper exception"):
        self.code = code
        self.message = message
        super().__init__(self.message)
