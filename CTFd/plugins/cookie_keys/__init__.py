from CTFd.models import db, Challenges

import subprocess
import datetime
import os

FLAGLEN = 16
FLAGPOOL = "/opt/flagpool"
SCHEMES = ["PKCS_1_5", "PKCS_OAEP"]

class PoolFlag(db.Model):
    __tablename__ = "pool_flags"
    id = db.Column(db.Integer, primary_key=True)
    queries = db.Column(db.Integer)
    flag = db.Column(db.Text)
    enc = db.Column(db.Text)
    scheme = db.Column(db.String(80))
    expiry = db.Column(db.DateTime)
    challenge_id = db.Column(db.Integer, default=0)

    def __init__(self, *args, **kwargs):
        super(PoolFlag, self).__init__(**kwargs)

    def __repr__(self):
        return "<PoolFlag {0} of {1} queries, scheme {2}, expiry {3}>".format(self.flag, self.queries, self.scheme, self.expiry)

def _collect_flags():
    dt = datetime.datetime.now()
    for fname in next(os.walk(FLAGPOOL))[2]:
        fpath = os.path.join(FLAGPOOL, fname)
        split = fname[:-len(".bin")].split("_")
        flag = split[-1].lower()
        queries = int(split[-2])
        scheme = "_".join(split[:-2])
        with open(os.path.join(fpath), "rb") as f:
            enc = f.read().hex()
        db.session.add(PoolFlag(queries=queries, flag=flag, enc=enc, scheme=scheme, expiry=dt, challenge_id=0))
        os.unlink(fpath)
    db.session.commit()

def _get_flag_from_db(scheme, min_queries=0, max_queries=1000000):
    candidates = PoolFlag.query.filter_by(challenge_id=0).filter_by(scheme=scheme).all()
    for candidate in candidates:
        if min_queries <= candidate.queries <= max_queries:
            return candidate
    return None

def _new_flag_for_challenge(chal, prev_exp=None):
    newflag = _get_flag_from_db(chal.scheme, chal.min_queries, chal.max_queries)
    if newflag is None:
        _collect_flags()
        newflag = _get_flag_from_db(chal.scheme, chal.min_queries, chal.max_queries)
    if newflag is None:
        newflag = _get_flag_from_db(chal.scheme)
    assert newflag is not None, "No available flags!"
    newflag.challenge_id = chal.id
    newflag.expiry = datetime.datetime.now() + datetime.timedelta(minutes=chal.interval)
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

def attempt_flag(challenge_id, val):
    flag = _get_active_flag(challenge_id)
    if flag.flag == val:
        return True, "Correct"
    old_flag = PoolFlag.query.filter_by(challenge_id=challenge_id).filter_by(flag=flag).first()
    if old_flag is not None:
        return False, "This flag has expired"
    return False, "Invalid flag"

def unregister_challenge(challenge_id):
    PoolFlag.query.filter_by(challenge_id=challenge_id).delete()

def load(app):
    app.db.create_all()
    filedir = os.path.dirname(__file__)
    sp = subprocess.Popen(["python", os.path.join(filedir, "generate_flags.py"), os.path.join(filedir, "priv.key.pem"), str(FLAGLEN), FLAGPOOL])
