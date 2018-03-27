import asyncio
import aiohttp
import bisect
import datetime
import operator
import contextlib
from . import logutil, constants
from collections import namedtuple
from googleapiclient.discovery import build as gapi_build
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logutil.get_logger(__name__)

_gapi_cse_service = None
_gapi_cse_id = None

ClassInfo = namedtuple('ClassInfo', ('name', 'crn', 'id', 'section',
                                     'seat_cap', 'seat_act', 'seat_rem',
                                     'wait_cap', 'wait_act', 'wait_rem'))

class AsyncContextManagerShield:
    def __init__(self, with_value):
        self.with_value = with_value

    def __bool__(self):
        return bool(self.with_value)

    async def __aenter__(self):
        return self.with_value

    async def __aexit__(self, exc_type, exc, tb):
        return False

def gapi_init(gapi_key, gapi_cse_id):
    global _gapi_cse_service
    global _gapi_cse_id
    _gapi_cse_service = gapi_build('customsearch', 'v1',
                                   developerKey=gapi_key,
                                   cache_discovery=False)
    _gapi_cse_id = gapi_cse_id

def autodiscover_sync(school_name):
    try:
        return urljoin(_gapi_cse_service.cse().list(
            q='inurl:{0!s}'.format(constants.BANNER_TEST_PATH),
            siteSearch=school_name,
            num=1,
            cx=_gapi_cse_id,
            fields='items/link'
            ).execute()['items'][0]['link'], '.')
    except (KeyError, IndexError):
        pass
    except Exception:
        logger.exception('failed to autodiscover Banner for school {0!s}',
                         school_name)

async def autodiscover(school_name):
    return await asyncio.get_event_loop().run_in_executor(
        None, autodiscover_sync, school_name)

async def test_url(url):
    url = urljoin(url, constants.BANNER_TEST_PATH)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=False) as resp:
            return resp.status == 200

def get_default_term():
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    year = now.year
    possible_terms = [datetime.datetime(year, month, 1, 0, 0, 0,
                                        tzinfo=datetime.timezone.utc)
                      for month in (2, 8)]
    possible_terms.append(datetime.datetime(year + 1, 2, 1, 0, 0, 0,
                                            tzinfo=datetime.timezone.utc))
    term = min(filter(lambda date: date >= now, possible_terms),
               key=lambda date: date - now)
    return term.year * 100 + term.month

async def get_class_info(base_url, crn, term=None, session=None):
    try:
        if crn == constants.TEST_CLASS_CRN:
            minute = datetime.datetime.now().minute
            return ClassInfo(constants.TEST_CLASS_NAME,
                             constants.TEST_CLASS_CRN,
                             constants.TEST_CLASS_COURSE_ID,
                             constants.TEST_CLASS_SECTION,
                             60, 60 - minute, minute, 0, 0, 0)
        if term is None:
            term = get_default_term()
        session_cm = (AsyncContextManagerShield(session)
                      or aiohttp.ClientSession())
        url = urljoin(base_url, constants.BANNER_DETAILS_PATH)
        params = {'term_in': str(term), 'crn_in': str(crn).rjust(5, '0')}
        async with session_cm as session:
            async with session.get(url, params=params) as resp:
                html = await resp.text()
        soup = BeautifulSoup(html, 'html.parser')
        details_tag = soup.find(class_='ddlabel')
        if details_tag is None:
            return None
        details = details_tag.get_text(strip=True).rsplit(' - ', 3)
        name, retrieved_crn, course_id, section = details
        retrieved_crn = int(retrieved_crn)
        string_getter = operator.attrgetter('string')
        seat_info_tags = soup.find_all(class_='dddefault')[1:7]
        seat_cap, seat_act, seat_rem, wait_cap, wait_act, wait_rem = \
                  map(int, map(string_getter, seat_info_tags))
        return ClassInfo(name, retrieved_crn, course_id, section, seat_cap,
                         seat_act, seat_rem, wait_cap, wait_act, wait_rem)
    except Exception:
        logger.exception('failed to retrieve class info for CRN {0!s} (term '
                         '{1!s}, Banner base URL: {2!s})', crn, term, base_url)
        return None
