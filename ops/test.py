from inc.onapp_helpers import get_onapp_bucket_access_controls


if __name__ == '__main__':
    vCPUs = 0
    RAM = 0
    storage_policy = 0
    access_controls = get_onapp_bucket_access_controls("1")
    for _ in access_controls:
        _['access_control']['type']
