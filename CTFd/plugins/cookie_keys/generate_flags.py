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

def gen_flags(keyfile, flaglen, flagdir, count_func, pref):
    if pref == "PKCS_1_5":
        pkcs_class = PKCS_1_5
    else:
        pkcs_class = PKCS_OAEP
    with open(keyfile, "rb") as f:
        key = RSA.import_key(f.read())
    pkcs = pkcs_class.new(key)
    flag = os.urandom(flaglen)
    enc = pkcs.encrypt(flag)
    rounds = count_func(key, enc, key.size_in_bytes())
    with open(os.path.join(flagdir, "_".join((pref, str(rounds), flag.hex()))) + ".bin", "wb") as f:
        f.write(enc)

MAX_FLAGS = 100
NUM_WORKERS = 2

def main():
    keyfile, flaglen, flagdir = sys.argv[1:]
    flaglen = int(flaglen)
    if not os.path.exists(flagdir):
        os.mkdir(flagdir)
    pool = multiprocessing.Pool(processes=NUM_WORKERS * 2)
    args = []
    for count_func, pref in ((bleichenbacher.count_rounds, "PKCS_1_5"),
                             (manger.count_rounds, "PKCS_OAEP")):
        args.append((keyfile, flaglen, flagdir, count_func, pref))
    while True:
        if len(os.listdir(flagdir)) >= MAX_FLAGS * 2:
            time.sleep(1)
        results = []
        for _ in range(NUM_WORKERS):
            for arg in args:
                results.append(pool.apply_async(gen_flags, arg))
        for result in results:
            result.wait()

if __name__ == "__main__":
    main()
