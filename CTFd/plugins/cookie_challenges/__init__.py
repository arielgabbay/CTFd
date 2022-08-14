from flask import Blueprint

import math

from CTFd.models import Challenges, db, Solves
from CTFd.plugins.challenges import BaseChallenge, CHALLENGE_CLASSES
from CTFd.plugins.cookie_keys import get_active_flag, unregister_challenge, attempt_flag, update_interval
from CTFd.plugins import register_plugin_assets_directory
from CTFd.utils.modes import get_model

class CookieChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "cookie"}
    id = db.Column(None, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True)
    initial = db.Column(db.Integer, default=0)
    minimum = db.Column(db.Integer, default=0)
    decay = db.Column(db.Integer, default=0)
    min_queries = db.Column(db.Integer, default=0)
    max_queries = db.Column(db.Integer, default=1000000)
    scheme = db.Column(db.String(80))
    interval = db.Column(db.Integer)

    def __init__(self, *args, **kwargs):
        super(CookieChallenge, self).__init__(**kwargs)
        self.value = kwargs["initial"]

class CTFdCookieChallenge(BaseChallenge):
    id = "cookie"
    name = "cookie"
    templates = {
            "create": "/plugins/cookie_challenges/assets/create.html",
            "update": "/plugins/cookie_challenges/assets/update.html",
            "view": "/plugins/cookie_challenges/assets/view.html"
            }
    scripts = {
            "create": "/plugins/cookie_challenges/assets/create.js",
            "update": "/plugins/cookie_challenges/assets/update.js",
            "view": "/plugins/cookie_challenges/assets/view.js"
            }
    route = "/plugins/cookie_challenges/assets/"
    blueprint = Blueprint(
            "cookie_challenges",
            __name__,
            template_folder="templates",
            static_folder="assets"
            )
    challenge_model = CookieChallenge

    @classmethod
    def calculate_value(cls, challenge):
        Model = get_model()
    
        solve_count = (
            Solves.query.join(Model, Solves.account_id == Model.id)
            .filter(
                Solves.challenge_id == challenge.id,
                Model.hidden == False,
                Model.banned == False,
            )
            .count()
        )
    
        # If the solve count is 0 we shouldn't manipulate the solve count to
        # let the math update back to normal
        if solve_count != 0:
            # We subtract -1 to allow the first solver to get max point value
            solve_count -= 1
    
        # It is important that this calculation takes into account floats.
        # Hence this file uses from __future__ import division
        value = (
            ((challenge.minimum - challenge.initial) / (challenge.decay ** 2))
            * (solve_count ** 2)
        ) + challenge.initial
    
        value = math.ceil(value)
    
        if value < challenge.minimum:
            value = challenge.minimum
    
        challenge.value = value
        db.session.commit()
        return challenge

    @classmethod 
    def update(cls, challenge, request):
        data = request.form or request.get_json()

        needs_update = (challenge.interval != int(data["interval"]))

        for attr, value in data.items():
            # We need to set these to floats so that the next operations don't operate on strings
            if attr in ("initial", "minimum", "decay", "min_queries", "max_queries", "interval"):
                value = float(value)
            setattr(challenge, attr, value)

        if needs_update:
            update_interval(challenge.id, int(data["interval"]))

        return CTFdCookieChallenge.calculate_value(challenge)

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)

        CTFdCookieChallenge.calculate_value(challenge)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        return attempt_flag(challenge.id, submission)

    @classmethod
    def delete(cls, challenge):
        unregister_challenge(challenge.id)
        super(CTFdCookieChallenge, cls).delete(challenge)

    @classmethod
    def read(cls, challenge):
        data = {
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
        }
        for attr in ("id", "name", "value", "initial", "decay", "minimum", "description",
                "connection_info", "category", "state", "max_attempts", "type", "min_queries",
                "max_queries", "scheme", "interval"):
            data[attr] = getattr(challenge, attr)
        _, enc, remaining = get_active_flag(challenge.id)
        print("Remaining: ", remaining)
        data["remaining"] = remaining
        data["enc"] = enc
        return data

def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["cookie"] = CTFdCookieChallenge
    register_plugin_assets_directory(app, base_path="/plugins/cookie_challenges/assets")

