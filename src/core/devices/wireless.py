

class Wireless:
    def __init__(self, name, params):
        self.name = name
        self.params = params
        
    @staticmethod
    def _enumerate(device):
        wirelesses = device.uci_request("get_all", ["wireless"])["result"]
        return wirelesses

    @staticmethod
    def enumerate(device):
        _wirelesses = Wireless._enumerate(device)
        wirelesses = []
        for wireless in _wirelesses:
            wirelesses.append(Wireless(wireless, _wirelesses[wireless]))
        return wirelesses
