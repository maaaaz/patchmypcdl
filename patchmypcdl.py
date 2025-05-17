#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from codecs import open
from pathlib import Path
import re
import os
import argparse
import functools
import requests
import types
import concurrent.futures
import secrets
import pprint

from lxml.etree import fromstring as fromstringxml
import pypdl

# Globals
VERSION = '1.0'
PATCHMYPC_FREE_DEFINITIONS = 'https://patchmypc.com/freeupdater/definitions/definitions.xml'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-i', '--input-file', help="Input file", required = True)
parser.add_argument('-s', '--do-not-download', help="Do not download anything, simply print download URLs", default = False, action='store_true')
parser.add_argument('-d', '--output-dir', help='Output dir (default ./patchmypcfree/)', default=os.path.abspath(os.path.join(os.getcwd(), './patchmypcfree/')))

def return_dl_url(pkg):
    return pkg['dl']['dl_url']    

def download_file(pkg, options):
    download_went_well = True
    pkgname, pkg = pkg
    pkg_dir = pkg['output_dir']
    pkg_url = ''
    
    if not os.path.exists(pkg_dir):
        Path(pkg_dir).mkdir(parents=True, exist_ok=True)
    
    if 'dl' in pkg.keys():
            pkg_url = return_dl_url(pkg)
    
    if pkg_url and pkg_dir:
        dl = pypdl.Pypdl(allow_reuse=False)

        dl_result = dl.start( url = pkg_url,
                              file_path = pkg_dir,
                              block=True,
                              clear_terminal=False,
                              display=False
                            )
        
        if dl.completed:
            if dl.failed:
                download_went_well = False

    return download_went_well

def download_files(pkgs_list, options):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futs = [ (pkg[0], executor.submit(functools.partial(download_file, pkg, options)))
            for pkg in pkgs_list.items() ]

    for pkgname, pkg_val in futs:
        ret = pkg_val.result()
        if not(ret):
            print("[!] Download of the package '%s' encountered in issue" % pkgname)

def list_dl_links(pkgs_list):
    for pkgname, pkg in pkgs_list.items():
        if 'dl' in pkg.keys():
            print(return_dl_url(pkg))
    return None

def extract(pkgname):
    elem  = {}

    content = requests.get(PATCHMYPC_FREE_DEFINITIONS).content.decode('utf-8')
    root = fromstringxml(bytes(content, encoding='utf-8'))

    link = root.xpath("//{}/text()".format(pkgname))
    link = link[0] if len(link) == 1 else ''

    if not(link):
        print("[!] Package '%s' is not found" % pkgname)
    
    else:
        elem['name'] = pkgname
        dl_elem = { 'dl_url': link }
        elem['dl'] = dl_elem
    
    return elem

def search(options, pkgs_list):
    with open(options.input_file, mode='r', encoding='utf-8') as fd_input:
        for line in fd_input:
            line = line.strip()
            if line:
                pkgname  = line
                output_dir = options.output_dir
                
                if ' | ' in line:
                    pkgname, output_dir = line.split(' | ')
                
                pkgs_list[pkgname] = {'output_dir': output_dir}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futs = [ (pkgname, executor.submit(functools.partial(extract, pkgname)))
            for pkgname, pkg in pkgs_list.items() ]
    
    for pkgname, pkg_extract in futs:
        if pkgname in pkgs_list.keys():
            pkgs_list[pkgname] = {**pkgs_list[pkgname], **pkg_extract.result()}
    
    return None

def main():
    global parser
    options = parser.parse_args()

    pkgs_list = {}
    search(options, pkgs_list)
    
    if options.do_not_download:
        print()
        list_dl_links(pkgs_list)
        return None

    download_files(pkgs_list, options)

    return None

if __name__ == "__main__" :
    main()
