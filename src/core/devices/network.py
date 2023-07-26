import device

class Network:
    @staticmethod
    def enumerate(device):
        networks = device.uci_request("get_all", ["network"])
        return networks.keys()
