import device

class Network:
    def __init__(self, params):
        self.params = params
        
    @staticmethod
    def _enumerate(device):
        networks = device.uci_request("get_all", ["network"])["result"]
        return networks

    @staticmethod
    def enumerate(device):
        _networks = _enumerate(device)
        networks = []
        for network in _networks:
            networks.append(Network(network))

    return networks
