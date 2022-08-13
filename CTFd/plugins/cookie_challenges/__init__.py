from flask import Blueprint

from CTFd.models import Challenges, db
from CTFd.plugins.challenges import BaseChallenge, CHALLENGE_CLASSES
from CTFd.plugins.cookie_keys import get_active_flag, unregister_challenge
from CTFd.plugins import register_plugin_assets_directory

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
    def attempt(cls, challenge, request):
        data = request.form or request.get_json()
        submission = data["submission"].strip().lower()
        flag, _, _ = get_active_flag(challenge.id)
        if submission == flag:
            return True, "Correct"
        return False, "Incorrect"

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
        data["remaining"] = remaining
        data["enc"] = enc
        return data

def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["cookie"] = CTFdCookieChallenge
    register_plugin_assets_directory(app, base_path="/plugins/cookie_challenges/assets")

