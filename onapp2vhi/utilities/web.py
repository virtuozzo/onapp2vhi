import requests
from os.path import join


MAX_CHUNK_SIZE = 8192


def download_file(uri: str, output_folder: str) -> str:
    """
    uri - url of file to be downloaded
    output_folder - destination folder where file is to be written
    return - path to the downloaded file
    """
    local_file_path = join(output_folder, uri.split('/')[-1])

    with requests.get(uri, stream=True) as r:
        r.raise_for_status()
        with open(local_file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=MAX_CHUNK_SIZE):
                f.write(chunk)

    return local_file_path
