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

import os
import glob
import hashlib
import json
import datetime

DATA_DIR_URL = 'https://raw.githubusercontent.com/cmsis-svd/cmsis-svd-data/refs/heads/main/data'
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def gen_index_json():
    svd_meta = {'date': None, 'data_dir_url': DATA_DIR_URL, 'data': {}}

    for svd in glob.glob(os.path.join(DATA_DIR, '**', '*.svd'), recursive=True):
        svd_dot = '.'.join(svd[len(DATA_DIR) + len(os.sep):-4].split(os.sep))
        print(f'[+] compute hash for: "{svd_dot}"')
        svd_hash = hashlib.md5(open(svd, 'rb').read()).hexdigest()
        svd_meta['data'][svd_dot] = {
            'hash': svd_hash, 'path': svd[len(DATA_DIR) + len(os.sep):]
        }

    svd_meta['date'] = datetime.datetime.now().timestamp()
    index_filename = os.path.join(os.path.dirname(__file__), 'index.json')

    with open(index_filename, 'w') as f:
        json.dump(svd_meta, f, sort_keys=True, indent=4)

    index_file_hash = hashlib.md5(open(index_filename, 'rb').read()).hexdigest()

    with open(os.path.join(os.path.dirname(__file__), 'index.md5'), 'w') as f:
        f.write(f'{os.path.basename(index_filename)} {index_file_hash}')


if __name__ == '__main__':
    gen_index_json()
