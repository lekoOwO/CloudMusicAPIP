#!/bin/env python2.7
# -*- coding: utf-8 -*-

import ipaddress
import random

f = open('china_ip_ranges.txt', 'r')
ip_ranges = f.readlines()
f.close()
random_ip_range = random.sample(ip_ranges, 1)[0].replace('\n', '')
random_ips = list(ipaddress.ip_network((random_ip_range)).hosts())

def get_china_ip():
  random_ip = random.sample(random_ips, 1)[0]
  return str(random_ip)

