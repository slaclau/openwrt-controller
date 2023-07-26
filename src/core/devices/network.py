import device

class Network:
    def __init__(self, name, params):
        self.name = name
        self.params = params
        
    @staticmethod
    def _enumerate(device):
        networks = device.uci_request("get_all", ["network"])["result"]
        return networks

    @staticmethod
    def enumerate(device):
        _networks = Network._enumerate(device)
        networks = []
        for network in _networks:
            networks.append(Network(network, _networks[network]))
        return networks

class Interface:
    def __init__(self, name, params):
        self.name = name
        self.params = params
    
    @staticmethod
    def _enumerate(device):
        interfaces = device.sys_request("net.deviceinfo", "")["error"]
        return interfaces
    
