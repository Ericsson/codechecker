
import hashlib

hashlib_md5_kwargs={'usedforsecurity':False}

def md5(utf8_str):
    global hashlib_md5_kwargs
    try:
        return hashlib.md5(utf8_str, **hashlib_md5_kwargs)
    except TypeError as e:
        hashlib_md5_kwargs={}
        return hashlib.md5(utf8_str, **hashlib_md5_kwargs)
