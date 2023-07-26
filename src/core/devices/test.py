import device
import network as nw
dev = device.Device("192.168.1.1")
dev.login()
networks = nw.Network.enumerate(dev)

for network in networks:
    print(network.params)

interfaces = nw.Interface._enumerate(dev)
print(interfaces)
for interface in interfaces:
    print(interface)
