from environs import Env

env = Env()
env.read_env()

bot_token = env.str("TOKEN")
open_ai_token = env.str("OPEN_AI_TOKEN")
access_token = env.str("ACCESS_TOKEN")

hour = env.int("HOUR")
minute = env.int("MINUTE")

amocrm_access_token = env.str("amocrm_access_token")
amocrm_subdomain = env.str("amocrm_subdomain")
amocrm_client_secret = env.str("amocrm_client_secret")
amocrm_id = env.str("amocrm_id")
