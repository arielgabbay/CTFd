from CTFd.models import db, Challenges

import subprocess
import datetime
import os

FLAGLEN = 16
FLAGPOOL = "/opt/flagpool"
SCHEMES = ["PKCS_1_5", "PKCS_OAEP", "NOPADDING"]

class PoolFlag(db.Model):
    __tablename__ = "pool_flags"
    id = db.Column(db.Integer, primary_key=True)
    queries = db.Column(db.Integer)
    flag = db.Column(db.Text)
    enc = db.Column(db.Text)
    scheme = db.Column(db.String(80))
    expiry = db.Column(db.DateTime)
    challenge_id = db.Column(db.Integer, default=0)
    category = db.Column(db.Text)

    def __init__(self, *args, **kwargs):
        super(PoolFlag, self).__init__(**kwargs)

    def __repr__(self):
        return "<PoolFlag {0} of {1} queries, scheme {2}, expiry {3}>".format(self.flag, self.queries, self.scheme, self.expiry)

def _collect_flags():
    dt = datetime.datetime.now()
    for category in next(os.walk(FLAGPOOL))[1]:
        catdir = os.path.join(FLAGPOOL, category)
        for padding in next(os.walk(catdir))[1]:
            paddir = os.path.join(catdir, padding)
            for fname in next(os.walk(paddir))[2]:
                fpath = os.path.join(paddir, fname)
                split = fname[:-len(".bin")].split("_")
                flag = split[-1].lower()
                queries = int(split[-2])
                with open(os.path.join(fpath), "rb") as f:
                    enc = f.read().hex()
                db.session.add(PoolFlag(queries=queries, flag=flag, enc=enc, scheme=padding, expiry=dt, challenge_id=0, category=category))
                os.unlink(fpath)
    db.session.commit()

def _get_flag_from_db(scheme, category, min_queries=0, max_queries=1000000):
    candidates = PoolFlag.query.filter_by(challenge_id=0).filter_by(scheme=scheme)
    if category is not None:
        candidates = candidates.filter_by(category=category).all()
    else:
        candidate = candidates.all()
    for candidate in candidates:
        if min_queries <= candidate.queries <= max_queries:
            return candidate
    return None

def _new_flag_for_challenge(chal, prev_exp=None):
    flag_category = chal.category if chal.category in ("Bleichenbacher", "Manger") else None
    newflag = _get_flag_from_db(chal.scheme, flag_category, chal.min_queries, chal.max_queries)
    if newflag is None:
        _collect_flags()
        newflag = _get_flag_from_db(chal.scheme, flag_category, chal.min_queries, chal.max_queries)
    if newflag is None:
        newflag = _get_flag_from_db(chal.scheme, None)
    assert newflag is not None, "No available flags!"
    newflag.challenge_id = chal.id
    if chal.interval > 0:
        newflag.expiry = datetime.datetime.now() + datetime.timedelta(minutes=chal.interval)
    else:
        newflag.expiry = datetime.datetime(3000, 1, 1)
    if prev_exp is not None:
        since_expiry = (datetime.datetime.now() - prev_exp).total_seconds() % (chal.interval * 60)
        newflag.expiry -= datetime.timedelta(seconds=since_expiry)
    db.session.commit()
    return newflag

def _get_active_flag(challenge_id):
    now = datetime.datetime.now()
    chal = Challenges.query.filter_by(id=challenge_id).first()
    assert chal is not None, "Challenge ID not found: {0}".format(challenge_id)
    flag = PoolFlag.query.filter_by(challenge_id=challenge_id).filter(PoolFlag.expiry >= now).first()
    if flag is None:
        flag = _new_flag_for_challenge(chal)
    return flag

def get_active_flag(challenge_id):
    flag = _get_active_flag(challenge_id)
    return flag.flag, flag.enc, int((flag.expiry - datetime.datetime.now()).total_seconds())

def update_interval(challenge_id, interval):
    flag = _get_active_flag(challenge_id)
    if interval > 0:
        flag.expiry = datetime.datetime.now() + datetime.timedelta(minutes=interval)
    else:
        flag.expiry = datetime.datetime(3000, 1, 1)

def attempt_flag(challenge_id, val):
    if len(val) != FLAGLEN * 2 or not all(c.isalnum() for c in val):
        return False, "Invalid flag value (should be a hex string of length 32; 16 encoded bytes)"
    flag = _get_active_flag(challenge_id)
    if flag.flag == val.lower():
        return True, "Correct"
    old_flag = PoolFlag.query.filter_by(challenge_id=challenge_id).filter_by(flag=val).first()
    if old_flag is not None:
        return False, "This flag has expired"
    return False, "Incorrect flag"

def unregister_challenge(challenge_id):
    PoolFlag.query.filter_by(challenge_id=challenge_id).delete()

def load(app):
    app.db.create_all()
    filedir = os.path.dirname(__file__)
    for category, padding in (("Bleichenbacher", "PKCS_1_5"), ("Bleichenbacher", "NOPADDING"),
                              ("Manger", "PKCS_OAEP"), ("Manger", "NOPADDING")):
        pooldir = os.path.join(FLAGPOOL, category, padding)
        sp = subprocess.Popen(["python", os.path.join(filedir, "generate_flags.py"), os.path.join(filedir, "priv.key.pem"), str(FLAGLEN), pooldir, category, padding])
