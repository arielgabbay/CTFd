from CTFd.models import db, Challenges

db = None

class PoolFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rounds = db.Column(db.Integer)
    flag = db.Column(db.Text)
    enc = db.Column(db.Text)
    scheme = db.Column(db.String(80))
    expiry = db.Column(db.DateTime)
    challenge_id = db.Column(None, db.ForeignKey("challenges.id"), primary_key=False, default=0)

    def __init__(self, *args, **kwargs):
        super(PoolFlag, self).__init__(**kwargs)

    def __repr__(self):
        return "<PoolFlag {0} of {1} rounds, scheme {2}, expiry {3}>".format(self.flag, self.rounds, self.scheme, self.expiry)

def _new_flag_for_challenge(chal, prev_exp=None):
    newflag = None
    candidates = PoolFlag.query.filter_by(challenge_id=0).all()
    for candidate in candidates:
        if newflag is None:
            newflag = candidate
        if chal.min_rounds <= candidate.rounds <= chal.max_rounds:
            newflag = candidate
            break
    assert newflag is not None, "No available flags!"
    newflag.challenge_id = chal.id
    newflag.expiry = datetime.datetime.now() + datetime.timedelta(minutes=chal.interval)
    if prev_exp is not None:
        since_expiry = (datetime.datetime.now() - prev_exp).total_seconds() % (chal.interval * 60)
        newflag.expiry -= datetime.timedelta(seconds=since_expiry)
    db.session.commit()
    return newflag

def get_active_flag(challenge_id):
    chal = Challenges.query.filter_by(id=challenge_id).first()
    assert chal is not None, "Challenge ID not found: {0}".format(challenge_id)
    flag = PoolFlag.query.filter_by(challenge_id=challenge_id).first()
    if flag is not None and flag.expiry < datetime.datetime.now():
        return flag.flag, flag.enc, int((flag.expiry - datetime.datetime.now()).total_seconds())
    flag = _new_flag_for_challenge(chal)
    return flag.flag, flag.enc, int((flag.expiry - datetime.datetime.now()).total_seconds())

def load(app):
    global db
    db = app.db
    app.db.create_all()
