#!/usr/bin/env python2
import os
import sys
import json
import click
import time
import xml.etree.ElementTree as KVMxml
from click_default_group import DefaultGroup
from inc.functions import run_command
from ops import logs
from cfg.o2v_config import Helper, OnAppAPICredentials, VHICLoudDefaults




