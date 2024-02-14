from environs import Env

env = Env()
env.read_env(".env")

AUTH_SERVICE_HOST = env.str("AUTH_SERVICE_HOST")
WRAPPER_SERVICE_HOST = env.str("WRAPPER_SERVICE_HOST")
ML_SERVICE_HOST = env.str("ML_SERVICE_HOST")
APP_PORT = env.int("APP_PORT")
SENTRY_DSN = env.str("SENTRY_DSN")
