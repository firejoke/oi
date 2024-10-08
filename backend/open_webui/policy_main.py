from .main import *
from .utils.policy_middleware import PolicyMiddleware


app.add_middleware(PolicyMiddleware)
