import json
import requests
import os

class Device:
    
    protocol = "http://"
    
    
    def __init__(self, ip, username="root", password="", protocol="http"):
        self.ip = ip
        self.username = username
        self.password = password
        
        self._base_url = protocol + "://" + ip + "/cgi-bin/luci/rpc/"
        
    def login(self):
        response = self._api_request("auth", 1, "login", [self.username, self.password])
        self.auth = response.json()["result"]
    
    def configure_rpc(self):
        if self.password == "":
            os.system(f"ssh {self.username}@1{self.ip} -c ipkg install luci-mod-rpc")
        else:
            raise NotImplementedError

    def _api_request(self, path, method, params):
        url = self._base_url + path
        data = {
            "method": method,
            "params": params,
        }
        try:
            return requests.post(url, data=json.dumps(data), params={"auth": self.auth})
        except AttributeError:
            return requests.post(url, data=json.dumps(data))
    
