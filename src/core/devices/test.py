import device
import network
dev = device.Device("192.168.1.1")
dev.login()
networks = nw.Network.enumerate(dev)

for nw in networks:
    print(nw.params)
