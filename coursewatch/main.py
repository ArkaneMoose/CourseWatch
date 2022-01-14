#!/usr/bin/env python3

import discord
import asyncio
import logging
import os
import argparse
import contextlib
import sys
import sqlite3
import datetime
import tldextract
import yaml
import functools
import humanize
import concurrent
from . import logutil, constants, banner, http
from urllib.parse import urlparse, urljoin
from collections import namedtuple, deque

client = discord.Client()
config = None
db = None
logger = logutil.get_logger(__name__)
conversations = set()
users = {}

ClassInfo = namedtuple('ClassInfo', ('db_id', 'name', 'term', 'crn', 'id',
                                     'section', 'seat_cap', 'seat_act',
                                     'seat_rem', 'wait_cap', 'wait_act',
                                     'wait_rem', 'seats_updated_seconds_ago'))


class ConfigReader:
    def __init__(self, *args):
        self.config_srcs = args

    def __getattr__(self, key):
        default_exists = False
        value = None
        for config_src in self.config_srcs:
            try:
                value = config_src(key)
            except (KeyError, AttributeError):
                default_exists = False
            else:
                if value is not None:
                    return value
                default_exists = True
        if not default_exists:
            raise ValueError("no value for required configuration option "
                             "{0!s}".format(repr(key)))
        return value


def get_term_and_crn_from_match(match):
    get_group = match.group
    crn_groups = constants.REGEX_CLASS_CRN_GROUPS
    try:
        crn = int(next(filter(None, (get_group(i) for i in crn_groups))))
    except StopIteration:
        return None, None
    term_groups = constants.REGEX_CLASS_TERM_GROUPS
    try:
        term = int(next(filter(None, (get_group(i) for i in term_groups))))
    except StopIteration:
        pass
    else:
        return term, crn
    year_groups = constants.REGEX_CLASS_YEAR_GROUPS
    try:
        year = int(next(filter(None, (get_group(i) for i in year_groups))))
    except StopIteration:
        return banner.get_default_term(), crn
    season_groups = constants.REGEX_CLASS_SEASON_GROUPS
    season = next(filter(None, (get_group(i) for i in season_groups)))
    return year * 100 + constants.BANNER_TERMS_BY_NAME[season.lower()], crn


def get_human_readable_term(term):
    year = term // 100
    season = constants.BANNER_TERMS_BY_NUMBER.get(term % 100, '(invalid term)')
    return '{season!s} {year!s}'.format(season=season, year=year)


def pluralize(word, num):
    if num != 1:
        return word + 's'
    return word


async def notify(user_id, summary, description=None):
    try:
        user = users[user_id]
    except KeyError:
        user = await client.fetch_user(user_id)
        users[user_id] = user
    message = await user.send(summary)
    if description is not None:
        await message.edit(content=description)


def dispatch_notifications(class_info):
    fmt_params = class_info._asdict()
    seat_or_waitlist = constants.MSG_PARAM_SEAT

    if class_info.seat_rem <= 0 and class_info.wait_cap > 0:
        fmt_params['seat_cap'] = class_info.wait_cap
        fmt_params['seat_rem'] = class_info.wait_rem
        seat_or_waitlist = constants.MSG_PARAM_WAITLIST_SPOT

    fmt_params['seat_or_waitlist_cap'] = pluralize(
        seat_or_waitlist, fmt_params['seat_cap'])
    fmt_params['seat_or_waitlist_rem'] = pluralize(
        seat_or_waitlist, fmt_params['seat_rem'])
    fmt_params['human_term'] = get_human_readable_term(class_info.term)

    summary = constants.USER_MSG_NOTIFICATION_SUMMARY.format(**fmt_params)
    description = constants.USER_MSG_NOTIFICATION_DESCRIPTION.format(
        **fmt_params)
    for user_id, in db.execute(constants.SQL_GET_USERS_TO_NOTIFY,
                               (class_info.db_id,)):
        asyncio.ensure_future(notify(user_id, summary, description))


async def get_class_info(school_id=None, crn=None, term=None, session=None,
                         id_in_db=None, force_refresh=False):
    if term is None:
        term = banner.get_default_term()
    cached_seat_rem = None
    cached_wait_rem = None
    notification_required = False
    try:
        if id_in_db is None:
            id_in_db, name, course_id, section, seat_cap, seat_act, seat_rem, \
                wait_cap, wait_act, wait_rem, seats_updated_seconds_ago \
                = next(db.execute(constants.SQL_GET_SEATS_BY_CLASS_INFO,
                                  (school_id, term, crn)))
        else:
            school_id, crn, term, name, course_id, section, seat_cap, \
                seat_act, seat_rem, wait_cap, wait_act, wait_rem, \
                seats_updated_seconds_ago = next(db.execute(
                    constants.SQL_GET_SEATS_BY_CLASS_ID, (id_in_db,)))
        cached_seat_rem = seat_rem
        cached_wait_rem = wait_rem
        if force_refresh:
            raise ValueError('forced refresh for school ID {0!s}, term {1!s}, '
                             'CRN {2!s} (age: {3!s} seconds)'.format(
                                 school_id, term, crn,
                                 seats_updated_seconds_ago))
        if seats_updated_seconds_ago > config.seat_data_max_age:
            raise ValueError('cached data out of date for school ID {0!s}, '
                             'term {1!s}, CRN {2!s} (age: {3!s} seconds)'
                             .format(school_id, term, crn,
                                     seats_updated_seconds_ago))
    except (StopIteration, ValueError):
        banner_url, = next(db.execute(constants.SQL_GET_SCHOOL_URL,
                                      (school_id,)))
        class_info = await banner.get_class_info(banner_url, crn, term=term,
                                                 session=session)
        if class_info is None:
            return None
        name, _, course_id, section, seat_cap, seat_act, seat_rem, wait_cap, \
            wait_act, wait_rem = class_info
        seats_updated_seconds_ago = 0
        with db:
            if id_in_db is None:
                id_in_db = db.execute(constants.SQL_CREATE_CLASS, (
                    school_id, term, crn, name, course_id, section, seat_cap,
                    seat_act, seat_rem, wait_cap, wait_act, wait_rem
                )).lastrowid
            else:
                notification_required = seat_rem != cached_seat_rem or (
                    seat_rem <= 0 and wait_rem != cached_wait_rem)
                db.execute(constants.SQL_UPDATE_SEAT_INFO, (
                    name, course_id, section, seat_cap, seat_act, seat_rem,
                    wait_cap, wait_act, wait_rem, id_in_db))
    result = ClassInfo(id_in_db, name, term, crn, course_id, section, seat_cap,
                       seat_act, seat_rem, wait_cap, wait_act, wait_rem,
                       seats_updated_seconds_ago)
    if notification_required:
        dispatch_notifications(result)
    return result


async def watch_iteration():
    logger.debug(constants.LOG_MSG_WATCHER_LOOP_ITERATION_START)
    async with http.create_aiohttp_session() as session:
        tasks = []
        for course_db_id, in db.execute(constants.SQL_GET_WATCHED_COURSES):
            tasks.append(asyncio.ensure_future(get_class_info(
                id_in_db=course_db_id, force_refresh=True, session=session)))
            logger.debug(constants.LOG_MSG_WATCHER_LOOP_DISPATCH.format(
                course_db_id))
        await asyncio.gather(*tasks, return_exceptions=True)
    logger.debug(constants.LOG_MSG_WATCHER_LOOP_ITERATION_END)


async def watcher():
    while True:
        asyncio.ensure_future(watch_iteration())
        await asyncio.sleep(config.seat_data_max_age)


class Conversation:
    NORMAL = 0
    HELLO = 1
    SCHOOL_NAME_REQUEST = 2
    BANNER_URL_REQUEST = 3
    RESET_CONFIRMATION = 4

    def reply(self, fmt, *args, **kwargs):
        return self.channel.send(fmt.format(*args, **kwargs))

    @property
    def msg_content(self):
        return self.message.content.strip()

    @property
    def msg_lc_content(self):
        return self.msg_content.lower()

    @property
    def author(self):
        return self.message.author

    @property
    def channel(self):
        return self.message.channel

    async def hello_state(self):
        with db:
            self.user_id = db.execute(constants.SQL_ADD_USER,
                                      (self.author.id, type(self).HELLO)
                                      ).lastrowid
        await self.reply(constants.USER_MSG_INTRODUCTION, self.author.mention)
        return type(self).SCHOOL_NAME_REQUEST

    async def check_reset(self):
        if self.msg_lc_content != 'reset':
            return False
        self.state |= type(self).RESET_CONFIRMATION
        await self.reply(constants.USER_MSG_RESET_CONFIRMATION)
        return True

    async def reset_confirm_state(self):
        if self.msg_lc_content == 'reset':
            with db:
                db.execute(
                    constants.SQL_RESET_USER_WATCHLIST, (self.user_id,)
                ).execute(constants.SQL_DELETE_USER, (self.user_id,))
            self.user_id = None
            await self.reply(constants.USER_MSG_RESET_DONE)
            return type(self).HELLO
        else:
            await self.reply(constants.USER_MSG_RESET_CANCELLED)
            return self.state & ~type(self).RESET_CONFIRMATION

    async def normal_state(self):
        if await self.check_reset():
            return
        match = constants.CMD_HELLO.match(self.msg_content)
        if match:
            await self.reply(constants.USER_MSG_HELLO, self.author.mention)
            return
        match = constants.CMD_HELP.match(self.msg_content)
        if match:
            await self.reply(constants.USER_MSG_HELP)
            return
        match = constants.CMD_DISCLAIMER.match(self.msg_content)
        if match:
            await self.reply(constants.USER_MSG_DISCLAIMER)
            return
        match = constants.CMD_CLASS_INFO.match(self.msg_content)
        if match:
            term, crn = get_term_and_crn_from_match(match)
            class_info = await get_class_info(self.school_id, crn, term=term)
            if class_info is not None:
                message = constants.USER_MSG_CLASS_ON_WATCHLIST
                try:
                    next(db.execute(constants.SQL_GET_WATCHLIST_RECORD,
                                    (self.user_id, class_info.db_id)))
                except StopIteration:
                    message = constants.USER_MSG_CLASS_NOT_ON_WATCHLIST
                fmt_params = class_info._asdict()
                fmt_params['human_term'] = get_human_readable_term(
                    class_info.term)
                fmt_params['human_timedelta'] = humanize.naturaltime(
                    datetime.timedelta(
                        seconds=class_info.seats_updated_seconds_ago))
                await self.reply(message, **fmt_params)
            else:
                await self.reply(constants.USER_MSG_CLASS_NOT_FOUND)
            return
        match = constants.CMD_CLASS_START_WATCHING.match(self.msg_content)
        if match:
            term, crn = get_term_and_crn_from_match(match)
            class_info = await get_class_info(self.school_id, crn, term=term)
            if class_info is not None:
                message = constants.USER_MSG_CLASS_ADDED_TO_WATCHLIST
                try:
                    next(db.execute(constants.SQL_GET_WATCHLIST_RECORD,
                                    (self.user_id, class_info.db_id)))
                except StopIteration:
                    with db:
                        db.execute(constants.SQL_ADD_TO_WATCHLIST,
                                   (self.user_id, class_info.db_id))
                else:
                    message = constants.USER_MSG_CLASS_ALREADY_ON_WATCHLIST
                fmt_params = class_info._asdict()
                fmt_params['human_term'] = get_human_readable_term(
                    class_info.term)
                fmt_params['human_timedelta'] = humanize.naturaltime(
                    datetime.timedelta(
                        seconds=class_info.seats_updated_seconds_ago))
                await self.reply(message, **fmt_params)
            else:
                await self.reply(constants.USER_MSG_CLASS_NOT_FOUND)
            return
        match = constants.CMD_CLASS_STOP_WATCHING.match(self.msg_content)
        if match:
            term, crn = get_term_and_crn_from_match(match)
            class_info = await get_class_info(self.school_id, crn, term=term)
            if class_info is not None:
                message = constants.USER_MSG_CLASS_REMOVED_FROM_WATCHLIST
                try:
                    watchlist_record, = next(db.execute(
                        constants.SQL_GET_WATCHLIST_RECORD,
                        (self.user_id, class_info.db_id)))
                except StopIteration:
                    message = constants.USER_MSG_CLASS_NOT_ON_WATCHLIST
                else:
                    with db:
                        db.execute(constants.SQL_REMOVE_FROM_WATCHLIST,
                                   (watchlist_record,))
                fmt_params = class_info._asdict()
                fmt_params['human_term'] = get_human_readable_term(
                    class_info.term)
                fmt_params['human_timedelta'] = humanize.naturaltime(
                    datetime.timedelta(
                        seconds=class_info.seats_updated_seconds_ago))
                await self.reply(message, **fmt_params)
            else:
                await self.reply(constants.USER_MSG_CLASS_NOT_FOUND)
            return
        match = constants.CMD_WATCHLIST.match(self.msg_content)
        if match:
            watchlist = []
            for term, crn, name, course_id, section, seat_cap, seat_rem, \
                    wait_cap, wait_rem in db.execute(
                        constants.SQL_GET_USER_WATCHLIST, (self.user_id,)):
                seat_or_waitlist = constants.MSG_PARAM_SEAT
                if seat_rem <= 0 and wait_cap > 0:
                    seat_cap = wait_cap
                    seat_rem = wait_rem
                    seat_or_waitlist = constants.MSG_PARAM_WAITLIST_SPOT
                watchlist.append(constants.USER_MSG_WATCHLIST_ENTRY.format(
                    id=course_id, section=section, name=name, crn=crn,
                    term=term, human_term=get_human_readable_term(term),
                    seat_cap=seat_cap, seat_rem=seat_rem,
                    seat_or_waitlist_cap=pluralize(seat_or_waitlist, seat_cap),
                ))
            if watchlist:
                lines = deque(watchlist)
                lines.appendleft(constants.USER_MSG_WATCHLIST.format(
                    humanize.apnumber(len(watchlist)),
                    '' if len(watchlist) == 1 else 's'))
                await self.reply('\n'.join(lines))
            else:
                await self.reply(constants.USER_MSG_WATCHLIST_EMPTY)
            return
        await self.reply(constants.USER_MSG_INVALID_COMMAND)

    async def school_name_req_state(self):
        if await self.check_reset():
            return
        extract_result = tldextract.extract(self.msg_content)
        if not extract_result.suffix:
            await self.reply(constants.USER_MSG_INVALID_SCHOOL_WEBSITE)
            return
        self.school_name = '.'.join(extract_result[1:]).lower()
        with db:
            db.execute(constants.SQL_ADD_SCHOOL_OR_IGNORE, (self.school_name,))
        cur = db.execute(constants.SQL_GET_SCHOOL_ID_URL, (self.school_name,))
        self.school_id, self.banner_base_url, autodetect_fail = next(cur)
        with db:
            db.execute(constants.SQL_SET_USER_SCHOOL_ID,
                       (self.school_id, self.user_id))
        if self.banner_base_url is None:
            if not autodetect_fail:
                self.banner_base_url = await banner.autodiscover(
                    self.school_name)
            if self.banner_base_url is not None:
                logger.info(constants.LOG_MSG_BANNER_URL_AUTODISCOVER_SUCCESS,
                            self.school_name, self.banner_base_url)
                with db:
                    db.execute(constants.SQL_SET_SCHOOL_URL,
                               (self.banner_base_url, self.school_id))
            else:
                if not autodetect_fail:
                    with db:
                        db.execute(constants.SQL_SET_SCHOOL_AUTODETECT_FAILED,
                                   (self.school_id,))
                await self.reply(constants.USER_MSG_BANNER_AUTODISCOVER_FAILED,
                                 self.school_name,
                                 datetime.datetime.utcnow().year)
                return type(self).BANNER_URL_REQUEST
        await self.reply(constants.USER_MSG_BANNER_AUTODISCOVER_SUCCESS)
        return type(self).NORMAL

    async def banner_url_req_state(self):
        if await self.check_reset():
            return
        banner_url_in_db, = next(db.execute(constants.SQL_GET_SCHOOL_URL,
                                            (self.school_id,)))
        if banner_url_in_db is not None:
            self.banner_base_url = banner_url_in_db
            await self.reply(constants.USER_MSG_BANNER_ALREADY_IN_DB)
            return type(self).NORMAL
        parse_result = urlparse(self.msg_content)
        if (parse_result.scheme.lower() not in ('http', 'https')
                or not parse_result.netloc):
            await self.reply(constants.USER_MSG_INVALID_URL)
            return
        extract_result = tldextract.extract(self.msg_content)
        banner_url_domain = '.'.join(filter(None, extract_result[1:])).lower()
        if not extract_result.suffix or banner_url_domain != self.school_name:
            await self.reply(constants.USER_MSG_URL_DOMAIN_MISMATCH,
                             banner_url_domain, self.school_name)
            return
        msg_to_edit = await self.reply(constants.USER_MSG_URL_TEST_IN_PROGRESS)
        banner_url = urljoin(self.msg_content, '.')
        if await banner.test_url(banner_url):
            self.banner_base_url = banner_url
            with db:
                db.execute(constants.SQL_SET_SCHOOL_URL, (banner_url,
                                                          self.school_id))
            logger.info(constants.LOG_MSG_BANNER_URL_MANUAL_SUCCESS,
                        self.school_name, self.banner_base_url)
            await msg_to_edit.edit(content=constants.USER_MSG_URL_TEST_SUCCESS)
            return type(self).NORMAL
        else:
            await msg_to_edit.edit(content=constants.USER_MSG_URL_TEST_FAILED)

    def __init__(self, message):
        self.message = message
        self.user_id = None
        try:
            result = next(db.execute(constants.SQL_GET_USER_BY_DISCORD_ID,
                                     (self.author.id,)))
        except StopIteration:
            self.state = type(self).HELLO
        else:
            self.user_id, self.school_id, self.state, self.school_name, \
                self.banner_base_url = result

    def run_state(self):
        try:
            return {
                type(self).NORMAL: self.normal_state,
                type(self).HELLO: self.hello_state,
                type(self).SCHOOL_NAME_REQUEST: self.school_name_req_state,
                type(self).BANNER_URL_REQUEST: self.banner_url_req_state,
            }[self.state]()
        except KeyError:
            if self.state & type(self).RESET_CONFIRMATION:
                return self.reset_confirm_state()
            raise ValueError('invalid state: {0!s}'.format(self.state))

    def __await__(self):
        while True:
            new_state = yield from self.run_state().__await__()
            if new_state is not None:
                self.state = new_state
            if self.user_id is not None:
                with db:
                    db.execute(constants.SQL_SET_USER_STATE, (self.state,
                                                              self.user_id))
            self.message = yield from client.wait_for(
                'message',
                check=lambda message: (
                    message.author == self.author
                    and message.channel == self.channel
                ),
            ).__await__()


@client.event
async def on_ready():
    logger.info(constants.LOG_MSG_READY, client.user.name, client.user.id)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.type != discord.ChannelType.private:
        if client.user.mentioned_in(message):
            await message.channel.send(constants.USER_MSG_NOT_IN_PM)
        return
    if message.author.id not in users:
        users[message.author.id] = message.author
    if message.author.id not in conversations:
        try:
            conversations.add(message.author.id)
            await Conversation(message)
        except concurrent.futures.CancelledError:
            pass
        except Exception:
            logger.exception('conversation with Discord user with ID {0!s} '
                             'raised an error', message.author.id)
            await message.channel.send(constants.USER_MSG_CRASH)
        finally:
            with contextlib.suppress(KeyError):
                conversations.remove(message.author.id)


def environ_getter(key):
    return os.environ[key.upper()]


def main():
    global db
    global config
    loop = asyncio.get_event_loop()
    try:
        parser = argparse.ArgumentParser(description=constants.DESCRIPTION)
        parser.add_argument('config_file', type=argparse.FileType('r'),
                            help=constants.ARG_HELP_CONFIG_FILE)
        parser.add_argument('--color', help=constants.ARG_HELP_COLOR)
        parser.add_argument('--log-level', help=constants.ARG_HELP_LOG_LEVEL)
        parser.add_argument('--db-file', help=constants.ARG_HELP_DB_FILE)
        args = parser.parse_args()
        config_file = yaml.safe_load(args.config_file)
        config = ConfigReader(functools.partial(getattr, args), environ_getter,
                              config_file.__getitem__,
                              constants.CONFIG_DEFAULTS.__getitem__)
        color = {
            'always': True,
            'auto': sys.stderr.isatty(),
            'no': False,
            True: True,
            False: False,
        }[config.color]
        if color:
            log_format = constants.LOG_FORMAT_COLORED
        else:
            log_format = constants.LOG_FORMAT
        log_level = getattr(logging, config.log_level.upper(), None)
        logging.basicConfig(format=log_format, level=log_level,
                            style=constants.LOG_FORMAT_STYLE)
        db = sqlite3.connect(config.db_file)
        db.executescript(constants.SQL_INITIALIZE)
        banner.gapi_init(config.google_api_token, config.google_cse_id)
        asyncio.ensure_future(watcher(), loop=loop)
        loop.run_until_complete(client.start(config.discord_api_token))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(client.close())
        pending = asyncio.all_tasks(loop=loop)
        gathered = asyncio.gather(*pending, loop=loop)
        try:
            gathered.cancel()
            loop.run_until_complete(gathered)
            # suppress warnings about unretrieved exceptions
            gathered.exception()
        except:
            pass
        loop.close()


if __name__ == '__main__':
    main()
