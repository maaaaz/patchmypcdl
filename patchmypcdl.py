#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from codecs import open
from pathlib import Path
import re
import os
import argparse
import requests
import functools
import types
import concurrent.futures
import pprint

from lxml.etree import fromstring as fromstringxml
import pypdl

# Globals
VERSION = '1.0'
PATCHMYPC_FREE_DEFINITIONS = 'https://patchmypc.com/freeupdater/definitions/definitions.xml'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
main_grp = parser.add_argument_group('Main parameters')
main_grp.add_argument('-i', '--input-file', help="Input file", required = True)
main_grp.add_argument('-o', '--output-dir', help='Output dir (default: ./patchmypcfree/)', default=os.path.abspath(os.path.join(os.getcwd(), './patchmypcfree/')))
main_grp.add_argument('-s', '--do-not-download', help="Do not download anything, simply print download URLs", default = False, action='store_true')

dl_grp = parser.add_argument_group('Download parameters')
dl_grp.add_argument('-d', '--display', help='Display download progress (default: False)', default=False, action='store_true')
dl_grp.add_argument('-c', '--concurrent', help='Number of concurrent downloads (default: 10)', default=10, type=int)
dl_grp.add_argument('-t', '--timeout', help='Max timeout in seconds to download a file (default: 30)', default=30, type=int)

def get_dl_url(pkg):
    return pkg['dl']['dl_url']

def download_files(pkgs_list, options):
    tasks = []

    dl = pypdl.Pypdl(allow_reuse=False, max_concurrent = options.concurrent)
    
    for pkgname, pkg in pkgs_list.items():
        pkg_dir = pkg['output_dir']
        pkg_url = ''

        if not os.path.exists(pkg_dir):
            Path(pkg_dir).mkdir(parents=True, exist_ok=True)
        
        if 'dl' in pkg.keys():
            pkg_url = get_dl_url(pkg)
        
        if pkg_url and pkg_dir:
            tasks.append( {'url': pkg_url, 'file_path': pkg_dir } )

    dl_result = dl.start( tasks = tasks,
                          block=True,
                          clear_terminal=False,
                          display=options.display,
                          timeout=aiohttp.ClientTimeout(sock_read=options.timeout)
                        )
    if dl.completed:
        dl_fails = dl.failed
        if dl_fails:
            for dl_fail in dl_fails:
                print("[!] The following package URL encountered an issue: '%s'" % dl_fail)
    
    return None

def list_dl_links(pkgs_list):
    for pkgname, pkg in pkgs_list.items():
        if 'dl' in pkg.keys():
            print(get_dl_url(pkg))
    return None

def extract(root, pkgname):
    elem  = {}

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

    content = requests.get(PATCHMYPC_FREE_DEFINITIONS).content.decode('utf-8')
    xmlroot = fromstringxml(bytes(content, encoding='utf-8'))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futs = [ (pkgname, executor.submit(functools.partial(extract, xmlroot, pkgname)))
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
