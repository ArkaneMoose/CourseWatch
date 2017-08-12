# CourseWatch

A Discord bot to watch the availability of courses on university registration
systems powered by Ellucian Banner.

# Installation

Requires Python 3. Use either of the following two commands:

```bash
python3 setup.py install
python3 -m pip install .
```

# Usage

```bash
coursewatch path/to/config.yaml
```

A configuration file in YAML format is required containing the configuration
options detailed below.

# `config.yaml` options

## Required

- `discord_api_token`: The OAuth token for your Discord bot. You can find this
  on your bot's developer page by clicking the *click to reveal* link next to
  **Token:** label.
- `google_api_token`: The API key for your Google Custom Search API. You can
  find this in the [Google Cloud Platform developer console in *Credentials*
  under *APIs & services*](https://console.cloud.google.com/apis/credentials)
  for your API project.
- `google_cse_id`: The Google Custom Search search engine ID for this bot to
  use. You can find this by clicking the *Search engine ID* button in the
  *Details* section of the *Basics* tab under *Setup* for the custom search
  engine you want to use on [Google Custom
  Search](https://cse.google.com/cse/all).

## Optional

- `seat_data_max_age`: The maximum age in seconds of course seating data
  before new data is retrieved. This is also the polling interval for course
  seating data when a course is being watched. Defaults to 30 seconds.
- `color`: Determines whether output should be in color. One of `no`, `auto`,
  or `always`. `auto` automatically detects whether output should be in color
  based on whether or not the standard error stream is a terminal. Defaults to
  `auto`.
- `log_level`: One of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG`.
  Defaults to Python's default, which is `WARNING`.
- `db_file`: The SQLite database file in which to store user and course
  information. Defaults to `coursewatch.db` in the current working directory.

## Command-line options and environment variables

The configuration file options `color`, `log_level`, and `db_file` can also be
passed as the `--color`, `--log-level`, and `--db-file` command-line options,
respectively.

All configuration options can be passed through their uppercase variants as
environment variables. For example, the `discord_api_token` configuration
option can be passed as the `DISCORD_API_TOKEN` environment variable.

The order of precedence for configuration options is as follows.

1. Command-line options
2. Environment variables
3. Configuration file options
4. Defaults
