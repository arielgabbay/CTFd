#!/usr/bin/python3.8
from Crypto.PublicKey import RSA
import Crypto.Cipher.PKCS1_v1_5 as PKCS_1_5
import Crypto.Cipher.PKCS1_OAEP as PKCS_OAEP
import random
import os
import multiprocessing
import itertools
import sys

import bleichenbacher
import manger

class RsaEnc:
    def __init__(self, key):
        self.key = key

    @classmethod
    def new(cls, key):
        return cls(key)
    
    def encrypt(buf):
        m = int.from_bytes(buf, byteorder="big")
        return pow(m, self.key.e, self.key.n).to_bytes(self.key.size_in_bytes(), byteorder="big")

ENC_CLASSES = {"PKCS_1_5": PKCS_1_5, "PKCS_OAEP": PKCS_OAEP, "NOPADDING": RsaEnc}
COUNT_FUNCS = {"Bleichenbacher": bleichenbacher.count_rounds, "Manger": manger.count_rounds}

MAX_FLAGS = 100

def gen_flags(keyfile, flaglen, flagdir, padding, category):
    pkcs_class = ENC_CLASSES[padding]
    count_func = COUNT_FUNCS[category]
    with open(keyfile, "rb") as f:
        key = RSA.import_key(f.read())
    pkcs = pkcs_class.new(key)
    flag = os.urandom(flaglen)
    enc = pkcs.encrypt(flag)
    rounds = count_func(key, enc, key.size_in_bytes())
    with open(os.path.join(flagdir, "_".join((str(rounds), flag.hex()))) + ".bin", "wb") as f:
        f.write(enc)

NUM_WORKERS = 2

def main():
    keyfile, flaglen, flagdir, category, padding_str = sys.argv[1:]
    flaglen = int(flaglen)
    if not os.path.exists(flagdir):
        os.mkdir(flagdir)
    pool = multiprocessing.Pool(processes=NUM_WORKERS)
    while True:
        if len(os.listdir(flagdir)) >= MAX_FLAGS:
            time.sleep(1)
        results = []
        for _ in range(NUM_WORKERS):
            results.append(pool.apply_async(gen_flags, (keyfile, flaglen, flagdir, padding, category)))
        for result in results:
            result.wait()

if __name__ == "__main__":
    main()
