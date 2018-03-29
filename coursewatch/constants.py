import re
import textwrap
from termcolor import colored

def unwrap(text):
    def newline_repl(match):
        newline_count = match.end() - match.start()
        if newline_count == 1: return ' '
        else: return '\n' * (newline_count - 1)
    return re.sub(r'\n+', newline_repl, textwrap.dedent(text).strip('\n'))

def command(regex):
    return re.compile('^' + re.sub(r'\s+', r'\s+', regex) + '$', re.I)

DESCRIPTION = 'Discord bot to watch availability of courses on Ellucian Banner'

CONFIG_DEFAULTS = {
    'color': 'auto',
    'log_level': '',
    'db_file': 'coursewatch.db',
    'seat_data_max_age': 30,
    }

ARG_HELP_CONFIG_FILE = 'YAML file in which tokens are stored'
ARG_HELP_COLOR = 'whether log output should be in color (no/auto/always)'
ARG_HELP_LOG_LEVEL = 'minimum logging level'
ARG_HELP_DB_FILE = 'database file (default: coursewatch.db)'

LOG_FORMAT = '[{asctime!s}] {name!s}: {message!s}'
LOG_FORMAT_COLORED = (colored('[{asctime!s}]', 'green') + ' '
                      + colored('{name!s}', 'yellow') + ': {message!s}')
LOG_FORMAT_STYLE = '{'

LOG_MSG_READY = 'Ready! Logged in as: {0!s} (ID: {1!s})'
LOG_MSG_BANNER_URL_AUTODISCOVER_SUCCESS = unwrap('''
    Successfully autodiscovered Banner base URL for {0!s}: {1!s}
    ''')
LOG_MSG_BANNER_URL_MANUAL_SUCCESS = unwrap('''
    Successfully entered manual Banner base URL for {0!s}: {1!s}
    ''')
LOG_MSG_WATCHER_LOOP_ITERATION_START = 'Watcher loop is executing tasks'
LOG_MSG_WATCHER_LOOP_DISPATCH = unwrap('''
    Watcher loop has requested course info for course with database ID {0!s}
    ''')
LOG_MSG_WATCHER_LOOP_ITERATION_END = unwrap('''
    Watcher loop has finished executing tasks
    ''')

USER_MSG_DISCLAIMER = unwrap('''
    Rishov Sarkar, creator of the CourseWatch bot, is not liable for any
    consequences as a result of using this bot. Your school may not
    allow the use of automated scripts such as this for watching course
    availability. It is up to you to make sure that you are allowed to
    use such a tool.


    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
    BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
    ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
    CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    ''')
USER_MSG_INTRODUCTION = unwrap('''
    Hello, {0!s}! I'm CourseWatch, a bot who tracks what courses are
    available when and lets you know when to register.


    First, a disclaimer:
    ''') + '\n' + USER_MSG_DISCLAIMER + '\n\n' + unwrap('''
    If, at any time, you'd like to restart the setup process, feel free
    to type `reset`.

    Let's jump right in. What's your school's website?
    ''')
USER_MSG_NOT_IN_PM = unwrap('''
    I'm CourseWatch, a bot who tracks what courses are available when
    and lets you know when to register.

    Send me a PM to start a conversation with me.
    ''')
USER_MSG_RESET_CONFIRMATION = unwrap('''
    Are you sure you want to reset my state? This will clear all data
    about you, including all classes you're watching. You will no longer
    be notified if any new seats open up until you go through the setup
    process again.

    Type `reset` again to confirm.
    ''')
USER_MSG_RESET_DONE = unwrap('''
    All your records have been cleared. Say anything to start a new
    conversation with me.
    ''')
USER_MSG_RESET_CANCELLED = unwrap('''
    You didn't type `reset`. Returning to previous state.
    ''')
USER_MSG_CLASS_INFO = unwrap('''
    Here is the current seating information for **{id!s} {section!s}**
    *{name!s}* (CRN {crn!s:0>5}, {human_term!s}):

    *Last updated {human_timedelta!s}*

    ```\n
             |  Capacity  |   Filled   | Available  \n
    ---------+------------+------------+------------\n
    Seats    | {seat_cap!s:>10} | {seat_act!s:>10} | {seat_rem!s:>10} \n
    Waitlist | {wait_cap!s:>10} | {wait_act!s:>10} | {wait_rem!s:>10} \n
    ```
    ''')
USER_MSG_CLASS_NOT_FOUND = unwrap('''
    Sorry, I couldn't find that class. Please check that the CRN is
    correct.
    ''')
USER_MSG_CLASS_ADDED_TO_WATCHLIST = USER_MSG_CLASS_INFO + '\n' + unwrap('''
    This class has been added to your watchlist. I will let you know if
    the availability of this class changes.
    ''')
USER_MSG_CLASS_REMOVED_FROM_WATCHLIST = USER_MSG_CLASS_INFO + '\n' + unwrap('''
    This class has been removed from your watchlist. You will no longer
    be notified if the availability of this class changes.
    ''')
USER_MSG_CLASS_ALREADY_ON_WATCHLIST = USER_MSG_CLASS_INFO + '\n' + unwrap('''
    This class is already on your watchlist. I will let you know if the
    availability of this class changes.
    ''')
USER_MSG_CLASS_NOT_ON_WATCHLIST = USER_MSG_CLASS_INFO + '\n' + unwrap('''
    This class is not on your watchlist. You will not be notified if the
    availability of this class changes.
    ''')
USER_MSG_CLASS_ON_WATCHLIST = USER_MSG_CLASS_INFO + '\n' + unwrap('''
    This class is on your watchlist. You will be notified if the
    availability of this class changes.
    ''')
USER_MSG_WATCHLIST = unwrap('''
    You are currently watching the following {0!s} course{1!s}:
    ''')
USER_MSG_WATCHLIST_EMPTY = unwrap('''
    You are currently not watching any courses.

    Type `watch <CRN>` to start watching a course, or type `help` for a
    list of commands.
    ''')
USER_MSG_WATCHLIST_ENTRY = unwrap('''
    **{id!s} {section!s}** *{name!s}* (CRN {crn!s:0>5}, {human_term!s}):
    {seat_rem!s}/{seat_cap!s} seat{seat_cap_plural!s} available
    ''')
USER_MSG_INVALID_SCHOOL_WEBSITE = unwrap('''
    Hmmm, that doesn't seem like a valid website. I'm looking for
    something like `http://www.gatech.edu/` or like `uga.edu`.
    Check what your school's website is, and let me know.
    ''')
USER_MSG_BANNER_AUTODISCOVER_FAILED = unwrap('''
    Hmmm, unfortunately I haven't heard of `{0!s}`, so I'm going to need
    a little more information from you. Bear with me.

    Your school needs to be using a program called Ellucian Banner in
    order for me to be able to check on its courses. Usually, it's named
    something school-specific, but it's a system a lot of schools use to
    allow students to view and register for courses.

    I'm going to need you to find a page on your school's website that
    uses this system. It will more than likely say `\u00A9 {1!s}
    Ellucian Company L.P. and its affiliates.` at the bottom of the
    page. But if it doesn't say that, find a page on your school's
    website that allows you to `Search by Term` and check if it says
    `bwckschd.p_disp_dyn_sched` in the URL bar. If it does, that's the
    page you need; paste its URL into this chat.

    If you can't find a page like I described, your school doesn't use
    Ellucian Banner, so I can't watch your courses for you. My deepest
    apologies. You can go ahead and remove this DM.
    ''')
USER_MSG_BANNER_AUTODISCOVER_SUCCESS = unwrap('''
    Awesome! You're good to go to start adding classes. Just say `watch
    <CRN>` to start watching the course with that CRN. (Type `help` to
    see a list of commands.)
    ''')
USER_MSG_BANNER_ALREADY_IN_DB = unwrap('''
    Looks like someone else at your school entered a valid URL before
    you did. The good news is that now you're ready to enter some
    classes! Just say `watch <CRN>` to start watching the course with
    that CRN. (Type `help` to see a list of commands.)
    ''')
USER_MSG_INVALID_URL = unwrap('''
    Hmm, that URL doesn't look valid. Try again.
    ''')
USER_MSG_URL_DOMAIN_MISMATCH = unwrap('''
    Hmm, that URL's domain name `{0!s}` doesn't seem to match your
    school `{1!s}`. Try again, or type `reset` to start over with the
    setup process if you mistyped your school's name.

    (If this is the right URL for your school's system, please contact
    the developer to have your school added manually.)
    ''')
USER_MSG_URL_TEST_IN_PROGRESS = unwrap('''
    All right, thanks! Give me a moment to test out that URL, please.
    ''')
USER_MSG_URL_TEST_SUCCESS = unwrap('''
    Awesome! I checked that URL, and it looks good to me. You're good to
    go ahead and start watching classes by saying `watch <CRN>`. (Type
    `help` to see a list of commands.)
    ''')
USER_MSG_URL_TEST_FAILED = unwrap('''
    Hmm, I checked that URL, and I didn't find what I expected to see.
    Try a different URL.
    ''')
USER_MSG_INVALID_COMMAND = unwrap('''
    Sorry, I don't understand what you want me to do.

    Type `help` for a list of commands.
    ''')
USER_MSG_HELLO = unwrap('''
    Hello, {0!s}!


    Type `help` for a list of commands.
    ''')
USER_MSG_HELP = unwrap('''
    Here are the commands you can give me:


    `<CRN>` will fetch the current seating information about the course
    specified by the CRN.\n
    `watch <CRN>`, `add <CRN>`, or `start watching <CRN>` will add the
    specified course to your watchlist.\n
    `remove <CRN>`, `delete <CRN>`, `unwatch <CRN>`, or `stop watching
    <CRN>` will remove the course from your watchlist.\n
    `list` or `watchlist` will display your current watchlist.\n
    `disclaimer` will display the disclaimer message.\n
    `help` will display this help message.


    The CRN (course reference number) is a five-digit number unique to
    each section of each course. This number can be found for each
    course through your school's registration system.

    If necessary, you can also specify a semester with the CRN. I try to
    make an intelligent guess about which semester you want based on the
    current date, but if you wish, you can manually override my guess by
    specifying the CRN in any of the following formats: `fall 2017
    <CRN>`, `201708/<CRN>`, `2017/fall/<CRN>`, or similar.


    If you'd like to test to make sure that notifications are working,
    you can add the CRN 00000 to your watchlist, which is a test course
    whose availability changes every minute.


    This bot was developed by Rishov Sarkar. Contact him if you have any
    questions, comments, or concerns.
    ''')
USER_MSG_NOTIFICATION_SUMMARY = unwrap('''
    {id!s} {section!s}: {seat_rem!s}/{seat_cap!s}
    seat{seat_cap_plural!s} available
    ''')
USER_MSG_NOTIFICATION_DESCRIPTION = unwrap('''
    **{id!s} {section!s}** *{name!s}* (CRN {crn!s:0>5}, {human_term!s})
    now has **{seat_rem!s} available seat{seat_rem_plural!s}** out of a
    total of {seat_cap!s} seat{seat_cap_plural!s}.
    ''')
USER_MSG_CRASH = unwrap('''
    Sorry! Your session crashed unexpectedly. If you just entered a
    command, it may not have been processed correctly. Please try again
    in a few seconds.

    If this problem continues to occur, please contact the developer,
    Rishov Sarkar.
    ''')

SQL_INITIALIZE = '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        discord_id TEXT UNIQUE NOT NULL,
        school_id INTEGER,
        state INTEGER NOT NULL,
        FOREIGN KEY(school_id) REFERENCES schools(id)
    );
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        banner_base_url TEXT,
        autodetect_failed INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        school_id INTEGER NOT NULL,
        term INTEGER NOT NULL,
        crn INTEGER NOT NULL,
        name TEXT,
        course_id TEXT,
        section TEXT,
        seat_cap INTEGER,
        seat_act INTEGER,
        seat_rem INTEGER,
        wait_cap INTEGER,
        wait_act INTEGER,
        wait_rem INTEGER,
        seats_last_updated INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY(school_id) REFERENCES schools(id)
    );
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(course_id) REFERENCES courses(id)
    );
    '''
SQL_ADD_USER = 'INSERT INTO users (discord_id, state) VALUES (?, ?)'
SQL_RESET_USER_WATCHLIST = 'DELETE FROM watchlist WHERE user_id = ?'
SQL_DELETE_USER = 'DELETE FROM users WHERE id = ?'
SQL_ADD_SCHOOL_OR_IGNORE = 'INSERT OR IGNORE INTO schools (name) VALUES (?)'
SQL_GET_SCHOOL_ID_URL = '''SELECT id, banner_base_url, autodetect_failed
                           FROM schools WHERE name = ?'''
SQL_SET_USER_SCHOOL_ID = 'UPDATE users SET school_id = ? WHERE id = ?'
SQL_SET_SCHOOL_URL = 'UPDATE schools SET banner_base_url = ? WHERE id = ?'
SQL_SET_SCHOOL_AUTODETECT_FAILED = '''UPDATE schools SET
                                      autodetect_failed = 1
                                      WHERE id = ?'''
SQL_GET_SCHOOL_URL = 'SELECT banner_base_url FROM schools WHERE id = ?'
SQL_GET_USER_BY_DISCORD_ID = '''SELECT users.id AS user_id, school_id,
                                state, name AS school_name,
                                banner_base_url FROM users LEFT JOIN
                                schools ON school_id = schools.id
                                WHERE users.discord_id = ?'''
SQL_SET_USER_STATE = 'UPDATE users SET state = ? WHERE id = ?'
SQL_GET_SEATS_BY_CLASS_INFO = '''SELECT id, name, course_id, section, seat_cap,
                       seat_act, seat_rem, wait_cap, wait_act, wait_rem,
                       (strftime('%s', 'now') - seats_last_updated) AS
                       seats_updated_seconds_ago FROM courses
                       WHERE school_id = ? AND term = ? AND crn = ?'''
SQL_GET_SEATS_BY_CLASS_ID = '''SELECT school_id, crn, term, name, course_id,
                               section, seat_cap, seat_act, seat_rem, wait_cap,
                               wait_act, wait_rem, (strftime('%s', 'now')
                               - seats_last_updated) AS
                               seats_updated_seconds_ago FROM courses
                               WHERE id = ?'''
SQL_UPDATE_SEAT_INFO = '''UPDATE courses SET name = ?, course_id = ?,
                       section = ?, seat_cap = ?, seat_act = ?,
                       seat_rem = ?, wait_cap = ?, wait_act = ?,
                       wait_rem = ?, seats_last_updated =
                       strftime('%s', 'now') WHERE id = ?'''
SQL_CREATE_CLASS = '''INSERT INTO courses (school_id, term, crn, name,
                      course_id, section, seat_cap, seat_act, seat_rem,
                      wait_cap, wait_act, wait_rem)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
SQL_GET_WATCHLIST_RECORD = '''SELECT id FROM watchlist WHERE user_id = ?
                              AND course_id = ?'''
SQL_ADD_TO_WATCHLIST = '''INSERT INTO watchlist (user_id, course_id)
                          VALUES (?, ?)'''
SQL_REMOVE_FROM_WATCHLIST = '''DELETE FROM watchlist WHERE id = ?'''
SQL_GET_USERS_TO_NOTIFY = '''SELECT discord_id FROM watchlist LEFT JOIN
                             users ON user_id = users.id
                             WHERE course_id = ?'''
SQL_GET_WATCHED_COURSES = '''SELECT DISTINCT course_id FROM watchlist'''
SQL_GET_USER_WATCHLIST = '''SELECT term, crn, name, courses.course_id AS
                            course_id, section, seat_cap, seat_rem FROM
                            watchlist INNER JOIN courses ON
                            watchlist.course_id = courses.id WHERE
                            user_id = ?'''

REGEX_CLASS = (
    r'(?:(fall|autumn|spring|summer)(?: |/)(\d{4,})(?: |/)|'
       r'(\d{4,})(?: |/)(fall|autumn|spring|summer)(?: |/)|(\d{6,})/)?(\d{5})')
REGEX_CLASS_SEASON_GROUPS = (1, 4)
REGEX_CLASS_YEAR_GROUPS = (2, 3)
REGEX_CLASS_TERM_GROUPS = (5,)
REGEX_CLASS_CRN_GROUPS = (6,)

CMD_CLASS_INFO = command(REGEX_CLASS)
CMD_CLASS_START_WATCHING = command(
    r'(?:add|watch|start watch(?:ing)?) {0!s}'.format(REGEX_CLASS))
CMD_CLASS_STOP_WATCHING = command(
    r'(?:remove|delete|unwatch|stop watch(?:ing)?) {0!s}'.format(REGEX_CLASS))
CMD_WATCHLIST = command(r'(?:my )?(?:watches|watch\s*list|list)')
CMD_HELP = command(r'(?:help|\?)')
CMD_DISCLAIMER = command(r'disclaimer')
CMD_HELLO = command(r'(?:hello|hi|hey|yo)')

BANNER_TERMS_BY_NAME = {
    'fall': 8,
    'autumn': 8,
    'spring': 2,
    'summer': 5,
    }
BANNER_TERMS_BY_NUMBER = {
    2: 'spring',
    5: 'summer',
    8: 'fall'
    }

TEST_CLASS_CRN = 0
TEST_CLASS_NAME = 'Test Class (changes every minute)'
TEST_CLASS_COURSE_ID = 'TEST 0000'
TEST_CLASS_SECTION = '0'

BANNER_TEST_PATH = 'bwckschd.p_disp_dyn_sched'
BANNER_DETAILS_PATH = 'bwckschd.p_disp_detail_sched'
