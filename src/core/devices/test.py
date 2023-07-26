import device
import network
dev = device.Device("192.168.1.1")
dev.login()
networks = network.Network.enumerate(dev)

for network in networks:
    print(network.params)

interfaces = network.Interface._enumerate(dev)
print(interfaces)
for interface in interfaces:
    print(interface)
