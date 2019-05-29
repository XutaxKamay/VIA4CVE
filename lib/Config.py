#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Config reader to read the configuration file
#
# Software is free software released under the "Modified BSD license"
#
# Copyright (c) 2016 	Pieter-Jan Moreels - pieterjan.moreels@gmail.com

# imports
import sys
import os
runPath = os.path.dirname(os.path.realpath(__file__))

import bz2
import configparser
import datetime
import gzip
import re
import urllib.parse
import urllib.request as req
import zipfile
import vulners

from io import BytesIO

vulners_api_key = None

class Configuration():
  ConfigParser = configparser.ConfigParser()
  ConfigParser.read(os.path.join(runPath, "../etc/configuration.ini"))
  defaults={'http_proxy': '', 'exitWhenNoSource': True}
  @classmethod
  def readSetting(cls, section, item, default):
    result = default
    try:
      if   type(default) == bool: result = cls.ConfigParser.getboolean(section, item)
      elif type(default) == int:  result = cls.ConfigParser.getint(section, item)
      else:                       result = cls.ConfigParser.get(section, item)
    except:
      pass
    return result

  @classmethod
  def getFeedData(cls, source, default, unpack=True):
    source = cls.readSetting("Sources", source, default)
    return cls.getFile(source, unpack) if source else None

  @classmethod
  def getProxy(cls):
    return cls.readSetting("Proxy", "http", cls.defaults['http_proxy'])

  @classmethod
  def exitWhenNoSource(cls):
    return cls.readSetting("Settings", "exitWhenNoSource", True)

  @classmethod
  def getFile(cls, getfile, unpack=True):
    vulners_url = "https://vulners.com/api/v3/archive/collection/?type="
    if vulners_url in getfile:
        global vulners_api_key
        if not (vulners_api_key):
            vulners_api_key = input("[!] Please enter your api key for vulners.com: ")
        vulners_api = vulners.Vulners(vulners_api_key)
        vulners_type = getfile[len(vulners_url):]
        print("[-] Fetching Vulners archive %s"%vulners_type)
        # Get response in a zipped json file
        response = vulners_api.vulners_get_request('archive', {'type':vulners_type})
        # Read zip file and return file data
        fzip = zipfile.ZipFile(BytesIO(response), 'r')
        if len(fzip.namelist())>0:
            data = BytesIO(fzip.read(fzip.namelist()[0]))
            return (data, None)
        return (None, None)
    else:
        print("[-] Fetching %s"%getfile)
        if cls.getProxy():
          proxy = req.ProxyHandler({'http': cls.getProxy(), 'https': cls.getProxy()})
          auth = req.HTTPBasicAuthHandler()
          opener = req.build_opener(proxy, auth, req.HTTPHandler)
          req.install_opener(opener)
        try:
          response = req.urlopen(getfile)
        except urllib.error.URLError as e:
          msg = "[!] Could not fetch file %s error -> %s"%(getfile, e)
          if cls.exitWhenNoSource(): 
              sys.exit(msg)
          else:                      
              print(msg)
        data = response.read()
        # TODO: if data == text/plain; charset=utf-8, read and decode
        if unpack:
          if   'gzip' in response.info().get('Content-Type'):
            data = gzip.GzipFile(fileobj = BytesIO(data))
          elif 'bzip2' in response.info().get('Content-Type'):
            data = BytesIO(bz2.decompress(data))
          elif 'zip' in response.info().get('Content-Type'):
            fzip = zipfile.ZipFile(BytesIO(data), 'r')
            if len(fzip.namelist())>0:
              data=BytesIO(fzip.read(fzip.namelist()[0]))
          # In case the webserver is being generic
          elif 'application/octet-stream' in response.info().get('Content-Type'):
            if data[:4] == b'PK\x03\x04': # Zip
              fzip = zipfile.ZipFile(BytesIO(data), 'r')
              if len(fzip.namelist())>0:
                data=BytesIO(fzip.read(fzip.namelist()[0]))
        return (data, response)
