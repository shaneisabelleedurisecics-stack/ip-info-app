# IP Address Information Tool

![CI](https://github.com/shaneisabelleedurisecics-stack/ip-info-app/actions/workflows/ci.yml/badge.svg)

A Python command-line application that shows network technicians their computer's
current **public IPv4 and IPv6 addresses**, plus **location and provider details**
(ISP, ASN, city, country, timezone) and the **hostname** for any IP address.

Built by Team TUKLAW for the Cisco DEVASC Project (Option 2).

## Features

| # | Feature | Function(s) |
|---|---------|-------------|
| 1 | Show public IPv4 address | `get_public_ipv4()`, `show_ipv4()` |
| 2 | Show public IPv6 address (with message if IPv6 is unavailable) | `get_public_ipv6()`, `show_ipv6()` |
| 3 | Full report: IPv4 + IPv6 + hostname + ISP/ASN/location | `build_full_report()`, `show_full_report()` |
| 4 | Look up any IP address, with validation | `show_ip_lookup()`, `get_ip_version()`, `is_public_ip()` |
| 5 | Save full report to a JSON file | `write_report()`, `save_report()` |
| 6 | Colored tables and menu | `print_table()`, `print_header()`, `main_menu()` |
| 7 | Error handling: no internet, timeout, rate limit, bad input | `fetch_json()`, `print_error()` |

### New in version 2.0 (Project Activity 4)

| # | Feature | Function(s) |
|---|---------|-------------|
| 8 | **Export report to CSV** (opens in Excel), menu option 6 | `report_to_rows()`, `write_report()` |
| 9 | **Reverse DNS lookup**: shows the hostname behind an IP | `get_hostname()` |
| 10 | **Command-line arguments**: run without the menu | `parse_args()`, `run_cli()` |

## APIs Used

All free, no API key required.

| API | Endpoint | Purpose |
|-----|----------|---------|
| ipify | `https://api.ipify.org?format=json` | Public IPv4 address |
| ipify | `https://api64.ipify.org?format=json` | Public IPv6 address (returns IPv4 if no IPv6 route) |
| ipapi.co | `https://ipapi.co/<ip>/json/` | ISP, ASN, location (free tier ~1,000 requests/day) |
| Python `socket` | built in | Reverse DNS (hostname) lookup |

## Installation

Requires Python 3.10 or newer.

```bash
git clone https://github.com/shaneisabelleedurisecics-stack/ip-info-app.git
cd ip-info-app
pip install -r requirements.txt
```

## Usage

**Interactive menu:**

```bash
python ip_info_app.py
```

```
  1) Show my public IPv4 address
  2) Show my public IPv6 address
  3) Full report (IPv4 + IPv6 + location/ISP details)
  4) Look up any IP address
  5) Save full report to a JSON file
  6) Save full report to a CSV file (opens in Excel)
  q) Quit
```

**Command-line options (new in v2.0):**

```bash
python ip_info_app.py --ipv4              # show public IPv4
python ip_info_app.py --ipv6              # show public IPv6
python ip_info_app.py --report            # full report
python ip_info_app.py --lookup 8.8.8.8    # look up any IP
python ip_info_app.py --save csv          # save report as CSV (or json)
python ip_info_app.py --help              # list all options
```

## Testing

The tests fake (mock) the API and DNS responses, so they run offline:

```bash
python -m unittest -v
```

29 tests cover IP validation, API calls, error handling, reverse DNS,
CSV/JSON export and command-line arguments.

## CI/CD Pipeline (GitHub Actions)

Every push to any branch and every pull request into `main` automatically runs
[`.github/workflows/ci.yml`](.github/workflows/ci.yml):

1. Check out the code on a fresh Ubuntu machine
2. Install Python and the libraries in `requirements.txt`
3. **Lint** the code with `flake8` (catches syntax errors and style problems)
4. **Run all unit tests** on Python 3.10, 3.11 and 3.12
5. **All tests passed** summary check

`main` is protected: a pull request can only be merged when the
**All tests passed** check is green. See the results in the repo's **Actions** tab.

A `Jenkinsfile` with the same install, lint and test stages is included for teams
that use Jenkins instead.

## Project Structure

```
ip-info-app/
├── .github/workflows/ci.yml   # GitHub Actions pipeline
├── .flake8                    # Lint settings
├── .gitignore                 # Files Git should ignore
├── Jenkinsfile                # Same pipeline for Jenkins
├── ip_info_app.py             # Main application
├── test_ip_info_app.py        # Unit tests (29 tests, mocked)
├── requirements.txt           # Python libraries
└── README.md                  # This file
```

## How to Continue This Project

1. Create a branch: `git checkout -b feature-your-idea`
2. Make your change, and **add a test** for it in `test_ip_info_app.py`.
3. Run `python -m unittest -v` locally before pushing.
4. Push and open a pull request. GitHub runs the pipeline automatically.
5. Merge only when the check is green and a teammate has approved it.

Code tips:

- **Change an API provider:** edit only the matching function (`get_public_ipv4`,
  `get_public_ipv6`, `get_ip_details` or `get_hostname`).
- **Show more fields:** add `(json_key, "Label")` pairs to `DETAIL_FIELDS`.
- **Add a menu option:** add it to `MENU_OPTIONS` and to the `actions` dictionary
  in `run_menu()`.
- **Add a command-line option:** add it in `parse_args()` and handle it in `run_cli()`.

**Remaining backlog:** bulk lookup from a file, IP change history, subnet calculator,
backup API provider, map view, GUI or web version, Docker container.

## Team

| Name | Role |
|------|------|
| Shane Isabelle Edurise | Scrum Leader |
| Vince Angelo Eugenio | Lead Developer and UI |
| Sean Leigh Enriquez | QA and Documentation |
