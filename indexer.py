"""

Copyright 2015-2024 cmsis-svd Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import datetime
import glob
import gzip
import hashlib
import json
import os
import tarfile

from typing import Dict, List

# Check for pyzstd for ZStandard compression support
try:
    have_zstd = True
    import pyzstd

    zstd_options = {
        pyzstd.CParameter.compressionLevel : 10,
        pyzstd.CParameter.checksumFlag : 1,
        pyzstd.CParameter.nbWorkers : 4,
    }
except ImportError:
    have_zstd = False

original_print = print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    original_print(*args, **kwargs)


DATA_DIR_URL = 'https://raw.githubusercontent.com/cmsis-svd/cmsis-svd-data/refs/heads/main/data'
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def compress_archive_gz(outfile: str, filenames: Dict[str, str]) -> None:
    with gzip.open(outfile, 'wb', compresslevel=9) as f_out:
        with tarfile.open(fileobj=f_out, mode='w') as tar:
            for arcname, source in sorted(filenames.items()):
                tar.add(source, arcname=arcname)

def compress_archive_zstd(outfile: str, filenames: Dict[str, str]) -> None:
    with pyzstd.ZstdFile(outfile, 'wb', level_or_option=zstd_options) as compressor:
        with tarfile.open(fileobj=compressor, mode='w') as tar:
            for arcname, source in sorted(filenames.items()):
                tar.add(source, arcname=arcname)

def compress_file_gz(outfile: str, filename: str) -> None:
    with open(filename, 'rb') as f_in:
        with gzip.open(outfile, 'wb', compresslevel=9) as f_out:
            f_out.writelines(f_in)

def compress_file_zstd(outfile: str, filename: str) -> None:
    with open(filename, 'rb') as f_in:
        with open(outfile, 'wb') as f_out:
            compressed_data = pyzstd.compress(f_in.read(), level_or_option=zstd_options)
            f_out.write(compressed_data)

def get_file_hash(filename: str) -> str:
    with open(filename, 'rb') as f:
        content = f.read()
        return hashlib.sha512(content).hexdigest()


def gen_index_json():
    svd_meta = {
        'source': {
            'date': None,
            'url': DATA_DIR_URL,
        },
        'files': {},
        'packages': {}
    }

    svd_archives = {}

    for svd in sorted(glob.glob(os.path.join(DATA_DIR, '**', '*.svd'), recursive=True)):
        svd_file = svd[len(DATA_DIR) + len(os.sep):]
        svd_dot = '.'.join(svd_file[:-4].split(os.sep))

        print(f'[+] processing file: "{svd_dot}" ...', end='')

        def containing_packages(filespec: str) -> List[str]:
            parts = filespec.split('.')
            return ['.'.join(parts[:i]) for i in range(1, len(parts))]

        package_for = containing_packages(svd_dot)
        for pkg in package_for:
            if pkg not in svd_archives:
                svd_archives[pkg] = {}
            svd_archives[pkg][svd_file] = svd

        svd_size = os.stat(svd).st_size

        svd_info = {
            'hash': None,
            'size': svd_size,
            'paths': {},
        }
        svd_info['paths']['plain'] = svd_file

        #print(f'[+] compute hash for file: "{svd_dot}"')
        print(' hash', end='')
        svd_hash = get_file_hash(svd)
        svd_info['hash'] = svd_hash

        #print(f'[+] compressing with gzip for file: "{svd_dot}"')
        print(' gzip', end='')
        compress_file_gz(svd + '.gz', svd)
        svd_info['paths']['gzip'] = svd_file + '.gz'

        if have_zstd:
            #print(f'[+] compressing with zstd for file: "{svd_dot}"')
            print(' zstd', end='')
            compress_file_zstd(svd + '.zstd', svd)
            svd_info['paths']['zstd'] = svd_file + '.zstd'

        svd_meta['files'][svd_dot] = svd_info

        print(' done')

    for pkg in svd_archives:
        print(f'[+] processing package: "{pkg}" ...', end='')

        pkg_files = svd_archives[pkg]
        pkg_info = {
            'contents': {pkg[:-4].replace(os.sep, '.'): pkg for pkg in pkg_files.keys()},
            'files': {}
        }

        #print(f'[+] compressing with gzip for package: "{pkg}"')
        print(' gzip', end='')
        pkg_file_gzip = pkg + '.tar.gz'
        pkg_path_gzip = os.path.join(DATA_DIR, pkg_file_gzip)
        compress_archive_gz(pkg_path_gzip, pkg_files)
        pkg_size_gzip = os.stat(pkg_path_gzip).st_size
        pkg_hash_gzip = get_file_hash(pkg_path_gzip)
        pkg_info['files']['gzip'] = {
            'name': pkg_file_gzip,
            'size': pkg_size_gzip,
            'hash': pkg_hash_gzip,
        }

        if have_zstd:
            print(' zstd', end='')
            #print(f'[+] compressing with zstd for package: "{pkg}"')
            pkg_file_zstd = pkg + '.tar.zstd'
            pkg_path_zstd = os.path.join(DATA_DIR, pkg_file_zstd)
            compress_archive_zstd(pkg_path_zstd, pkg_files)
            pkg_size_zstd = os.stat(pkg_path_zstd).st_size
            pkg_hash_zstd = get_file_hash(pkg_path_zstd)
            pkg_info['files']['zstd'] = {
                'name': pkg_file_zstd,
                'size': pkg_size_zstd,
                'hash': pkg_hash_zstd,
            }

        svd_meta['packages'][pkg] = pkg_info

        print(' done')

    print(f'[+] Writing metadata index ...', end='')
    print(' json', end='')
    svd_meta['source']['date'] = datetime.datetime.now().timestamp()

    index_filename = os.path.join(DATA_DIR, 'index.json')

    with open(index_filename, 'w') as f:
        json.dump(svd_meta, f, sort_keys=True, indent=4)

    index_file_plain = get_file_hash(index_filename)

    print(' gzip', end='')
    compress_file_gz(index_filename + '.gz', index_filename)
    if have_zstd:
        compress_file_zstd(index_filename + '.zstd', index_filename)

    index_file_gzip = get_file_hash(index_filename + '.gz')
    if have_zstd:
        print(' zstd', end='')
        index_file_zstd = get_file_hash(index_filename + '.zstd')

    print(' hash', end='')
    with open(os.path.join(DATA_DIR, 'index.hash'), 'w') as f:
        f.write(f'{os.path.basename(index_filename)} {index_file_plain}\n')
        f.write(f'{os.path.basename(index_filename) + '.gz'} {index_file_gzip}\n')
        if have_zstd:
            f.write(f'{os.path.basename(index_filename) + '.zstd'} {index_file_zstd}\n')

    print(' done')


if __name__ == '__main__':
    gen_index_json()
