#!/home/sebastien/git/openwrt-controller-venv/bin/python

import device
import network
import wireless
dev = device.Device("192.168.1.1")
dev.login()

networks = network.Network.enumerate(dev)
wirelesses = wireless.Wireless.enumerate(dev)

for nw in networks:
    print(nw.params)

for wl in wirelesses:
    print(wl.params)