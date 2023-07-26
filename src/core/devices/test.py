import device
import network
dev = device.Device("192.268.1.1")
dev.login()
networks = network.Network.enumerate(dev)

print(networks)
