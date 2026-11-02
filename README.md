# IP Address Information Tool

A Python command-line application that shows network technicians their computer's
current **public IPv4 and IPv6 addresses**, plus **location and provider details**
(ISP, ASN, city, country, timezone) for any IP address.

Built for the Cisco DEVASC Project, Option 2.

## Features

| # | Feature | Function(s) |
|---|---------|-------------|
| 1 | Show public IPv4 address | `get_public_ipv4()`, `show_ipv4()` |
| 2 | Show public IPv6 address (with message if IPv6 is unavailable) | `get_public_ipv6()`, `show_ipv6()` |
| 3 | Full report: IPv4 + IPv6 + ISP/ASN/location | `build_full_report()`, `show_full_report()` |
| 4 | Look up any IP address, with validation | `lookup_custom_ip()`, `get_ip_version()`, `is_public_ip()` |
| 5 | Save full report to a timestamped JSON file | `save_report()` |
| 6 | Colored tables and menu | `print_table()`, `print_header()`, `main_menu()` |
| 7 | Error handling: no internet, timeout, rate limit, bad input | `fetch_json()`, `print_error()` |

## APIs Used

All free, no API key required.

| API | Endpoint | Purpose |
|-----|----------|---------|
| ipify | `https://api.ipify.org?format=json` | Public IPv4 address |
| ipify | `https://api64.ipify.org?format=json` | Public IPv6 address (returns IPv4 if no IPv6 route) |
| ipapi.co | `https://ipapi.co/<ip>/json/` | ISP, ASN, location (free tier ~1,000 requests/day) |

## Installation

Requires Python 3.8 or newer.

```bash
git clone https://github.com/<username>/ip-info-app.git
cd ip-info-app
pip install -r requirements.txt
```

## Usage

```bash
python ip_info_app.py
```

Then choose an option from the menu:

```
  1) Show my public IPv4 address
  2) Show my public IPv6 address
  3) Full report (IPv4 + IPv6 + location/ISP details)
  4) Look up any IP address
  5) Save full report to a JSON file
  q) Quit
```

## Running the Tests

The tests fake the API responses, so they work offline:

```bash
python -m unittest test_ip_info_app.py -v
```

## Project Structure

```
ip-info-app/
├── ip_info_app.py        # Main application
├── test_ip_info_app.py   # Unit tests (13 tests, mocked APIs)
├── requirements.txt      # Python libraries
├── .gitignore            # Files Git should ignore
└── README.md             # This file
```

## How to Continue This Project

- **Change an API provider:** edit only the matching function (`get_public_ipv4`,
  `get_public_ipv6` or `get_ip_details`). The rest of the app uses their return values.
- **Show more fields:** add `(json_key, "Label")` pairs to `DETAIL_FIELDS`.
- **Add a menu option:** add it to `MENU_OPTIONS`, write a function, and map it in
  the `actions` dictionary inside `main()`.
- **Backlog ideas:** see the project document (CSV export, GUI, map view, reverse DNS,
  subnet calculator, IP change history).

## Team

| Name | Role |
|------|------|
| [Name 1] | Scrum Leader |
| [Name 2] | Lead Developer |
| [Name 3] | Developer – UI |
| [Name 4] | QA and Documentation |
