"""
Note to self: https://stackoverflow.com/questions/18713086/virtualenv-wont-activate-on-windows
              Set-ExecutionPolicy Unrestricted -Force -Scope CurrentUser
"""
import logging
from datetime import timedelta
from tomllib import load as load_toml
from typing import Any

from dotenv import dotenv_values
from requests import Session

from bronnen import Amsterdam, Bammens, Welvaarts
from local.pull import pull_amsterdam, pull_bammens, pull_welvaarts
from local.push import push_containers, push_gebieden, push_wegingen
from local.push.tools import last_monday
from local.storage import stored_pickle

logger = logging.getLogger(__name__)


def load_config() -> dict[str, Any]:
    with open('config.toml', 'rb') as f:
        return load_toml(f)


def load_env() -> dict[str, str]:
    env = dotenv_values('.env')
    return {
        'bammens': (env['BAMMENS_USERNAME'], env['BAMMENS_PASSWORD']),
        'welvaarts': (env['WELVAARTS_USERNAME'], env['WELVAARTS_PASSWORD']),
    }


def main() -> None:
    tokens = load_env()
    config = load_config()

    logger.info('Haal alle nieuwe data up uit bronsystemen...')

    with (stored_pickle(config['sessie']['amsterdam'], Session) as ses_a,
          stored_pickle(config['sessie']['bammens'], Session) as ses_b,
          stored_pickle(config['sessie']['welvaarts'], Session) as ses_w):

        amsterdam_api = Amsterdam(ses_a)
        bammens_api = Bammens(ses_b, auth=tokens['bammens'])
        welvaarts_api = Welvaarts(ses_w, auth=tokens['welvaarts'])

        pull_amsterdam(amsterdam_api, config['data'], rate_limit=timedelta(days=2))
        pull_bammens(bammens_api, config['data'], rate_limit=timedelta(hours=8))
        pull_welvaarts(welvaarts_api, config['data'], rate_limit=timedelta(minutes=1))

    logger.info('Combineer de gegevens en produceer output bestanden...')

    push_gebieden(config['html']['gebieden'], config['data'])
    push_containers(config['html']['containers'], config['data'])
    push_wegingen(config['html']['wegingen'], config['html']['wegingen-updates'],
                  config['data'], config['html'], after=last_monday(n_weeks_back=4))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # logging.getLogger('urllib3').setLevel(logging.WARN)
    logging.getLogger('matplotlib').setLevel(logging.WARN)
    main()
