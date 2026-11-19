"""
IP Address Information Application  (version 2.0)
=================================================
DEVASC Project - Option 2: IPv4/IPv6 Address Application

Purpose:
    A command-line tool for network technicians that shows the computer's
    current public IPv4 and IPv6 addresses, plus geolocation and provider
    details (ISP, ASN, country, etc.) for any IP address.

New in version 2.0 (Project Activity 4, from our backlog):
    - Export reports to CSV, which opens directly in Excel (menu option 6).
    - Reverse DNS lookup: shows the hostname behind an IP (e.g. dns.google).
    - Command-line arguments, so the app can run without the menu:
          python ip_info_app.py --ipv4
          python ip_info_app.py --lookup 8.8.8.8
          python ip_info_app.py --save csv

APIs used (all free, no API key required):
    - ipify IPv4 : https://api.ipify.org?format=json
    - ipify IPv6 : https://api64.ipify.org?format=json
                   (returns IPv6 if available, otherwise falls back to IPv4)
    - ipapi.co   : https://ipapi.co/<ip>/json/
                   (location, ISP, ASN; free tier is about 1,000 requests/day)
    - Reverse DNS uses Python's built-in socket module (no API needed).

How to run:
    pip install -r requirements.txt
    python ip_info_app.py            (interactive menu)
    python ip_info_app.py --help     (list command-line options)

How to test:
    python -m unittest -v
    Tests also run automatically on GitHub (see .github/workflows/ci.yml).

How to extend (for future teams):
    - Each API call lives in its own function (get_public_ipv4, get_public_ipv6,
      get_ip_details, get_hostname). To switch providers, change only that function.
    - To show more fields, add entries to DETAIL_FIELDS below.
    - To add a menu option, add a line in MENU_OPTIONS and an entry in the
      `actions` dictionary inside run_menu().
    - To add a command-line option, add it in parse_args() and handle it in run_cli().
    - Always add a test in test_ip_info_app.py; GitHub blocks merging if any test fails.
"""

import argparse
import csv
import ipaddress
import json
import os
import socket
from datetime import datetime

import requests
from colorama import Fore, Style, init
from tabulate import tabulate

# Make colors work on Windows terminals too; reset color after each print.
init(autoreset=True)

__version__ = "2.0"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IPV4_URL = "https://api.ipify.org?format=json"
IPV6_URL = "https://api64.ipify.org?format=json"
DETAILS_URL = "https://ipapi.co/{ip}/json/"
TIMEOUT_SECONDS = 10  # Stop waiting for an API after this many seconds
REPORT_FORMATS = ("json", "csv")  # File types the report can be saved as

# Fields shown in the details table: (key in ipapi.co JSON, label for the user)
DETAIL_FIELDS = [
    ("ip", "IP Address"),
    ("version", "IP Version"),
    ("org", "ISP / Organization"),
    ("asn", "ASN"),
    ("city", "City"),
    ("region", "Region"),
    ("country_name", "Country"),
    ("country_code", "Country Code"),
    ("postal", "Postal Code"),
    ("timezone", "Timezone"),
    ("latitude", "Latitude"),
    ("longitude", "Longitude"),
]

MENU_OPTIONS = [
    ("1", "Show my public IPv4 address"),
    ("2", "Show my public IPv6 address"),
    ("3", "Full report (IPv4 + IPv6 + location/ISP details)"),
    ("4", "Look up any IP address"),
    ("5", "Save full report to a JSON file"),
    ("6", "Save full report to a CSV file (opens in Excel)"),
    ("q", "Quit"),
]


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------
def fetch_json(url):
    """Send a GET request to `url` and return the JSON response as a dict.

    Returns None (and prints a friendly error) if anything goes wrong,
    so the rest of the program never crashes because of a network problem.
    """
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS,
                                headers={"User-Agent": "devasc-ip-info-app/2.0"})
        if response.status_code == 429:
            print_error("API rate limit reached. Please wait a minute and try again.")
            return None
        response.raise_for_status()  # Raise an error for 4xx/5xx codes
        return response.json()
    except requests.exceptions.ConnectionError:
        print_error("No connection. Check your internet and try again.")
    except requests.exceptions.Timeout:
        print_error(f"The API did not answer within {TIMEOUT_SECONDS} seconds.")
    except requests.exceptions.HTTPError as err:
        print_error(f"API returned an error: {err}")
    except ValueError:
        print_error("The API response was not valid JSON.")
    return None


def get_public_ipv4():
    """Return the computer's public IPv4 address as a string, or None."""
    data = fetch_json(IPV4_URL)
    return data.get("ip") if data else None


def get_public_ipv6():
    """Return the computer's public IPv6 address as a string, or None.

    api64.ipify.org returns an IPv4 address when the network has no IPv6
    route, so we check the version before returning it.
    """
    data = fetch_json(IPV6_URL)
    if not data:
        return None
    ip = data.get("ip")
    if ip and get_ip_version(ip) == 6:
        return ip
    return None  # Network has no IPv6 connectivity


def get_ip_details(ip=""):
    """Return location/ISP details for `ip` as a dict, or None.

    If `ip` is empty, ipapi.co returns details for the caller's own IP.
    """
    url = DETAILS_URL.format(ip=ip) if ip else "https://ipapi.co/json/"
    data = fetch_json(url)
    if data and data.get("error"):
        # ipapi.co sends {"error": true, "reason": "..."} for bad or reserved IPs
        print_error(f"Lookup failed: {data.get('reason', 'unknown reason')}")
        return None
    return data


def get_hostname(ip):
    """NEW (v2.0): Reverse DNS lookup. Return the hostname for `ip`, or None.

    Example: 8.8.8.8 -> "dns.google". Many IPs have no hostname registered,
    so None is a normal result, not an error.
    """
    if not ip:
        return None
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError, UnicodeError):
        return None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_ip_version(ip):
    """Return 4 or 6 for a valid IP address string, or None if invalid."""
    try:
        return ipaddress.ip_address(ip.strip()).version
    except ValueError:
        return None


def is_public_ip(ip):
    """Return True if `ip` is a public (globally routable) address."""
    try:
        return ipaddress.ip_address(ip.strip()).is_global
    except ValueError:
        return False


def build_details_rows(details):
    """Turn the ipapi.co dict into [label, value] rows for the table."""
    rows = []
    for key, label in DETAIL_FIELDS:
        value = details.get(key)
        if value not in (None, ""):
            rows.append([label, value])
    return rows


def build_full_report():
    """Collect IPv4, IPv6, hostname and details into one dict.

    Used by menu options 3, 5 and 6 and by the --report and --save arguments.
    """
    ipv4 = get_public_ipv4()
    ipv6 = get_public_ipv6()
    main_ip = ipv4 or ipv6 or ""
    details = get_ip_details(main_ip)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "public_ipv4": ipv4,
        "public_ipv6": ipv6,
        "hostname": get_hostname(main_ip),
        "details": details,
    }


def report_to_rows(report):
    """NEW (v2.0): Flatten a full report into [Field, Value] rows.

    Used to write the CSV file, so the same rows appear in Excel as on screen.
    """
    rows = [
        ["Generated At", report.get("generated_at") or ""],
        ["Public IPv4", report.get("public_ipv4") or "Not available"],
        ["Public IPv6", report.get("public_ipv6") or "Not available"],
        ["Hostname", report.get("hostname") or "Not available"],
    ]
    if report.get("details"):
        rows.extend(build_details_rows(report["details"]))
    return rows


def write_report(report, fmt="json", folder=""):
    """Save `report` to a timestamped file and return its path.

    `fmt` must be "json" or "csv". CSV files use UTF-8 with a BOM
    ("utf-8-sig") so Excel shows special characters correctly.
    Raises ValueError for an unknown format and OSError if the file
    cannot be written.
    """
    fmt = fmt.lower()
    if fmt not in REPORT_FORMATS:
        raise ValueError(f"Unknown format '{fmt}'. Use one of: {', '.join(REPORT_FORMATS)}")
    filename = f"ip_report_{datetime.now():%Y%m%d_%H%M%S}.{fmt}"
    path = os.path.join(folder, filename)
    if fmt == "json":
        with open(path, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4)
    else:
        with open(path, "w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Field", "Value"])
            writer.writerows(report_to_rows(report))
    return path


# ---------------------------------------------------------------------------
# Display functions
# ---------------------------------------------------------------------------
def print_header(text):
    """Print a cyan section header."""
    print("\n" + Fore.CYAN + Style.BRIGHT + "=" * 60)
    print(Fore.CYAN + Style.BRIGHT + text.center(60))
    print(Fore.CYAN + Style.BRIGHT + "=" * 60)


def print_error(text):
    """Print an error message in red."""
    print(Fore.RED + "[ERROR] " + text)


def print_table(rows, headers=("Field", "Value")):
    """Print rows as a formatted table with yellow headers."""
    colored_headers = [Fore.YELLOW + Style.BRIGHT + h + Style.RESET_ALL for h in headers]
    print(tabulate(rows, headers=colored_headers, tablefmt="fancy_grid"))


def show_ipv4():
    """Menu option 1 / --ipv4: display the public IPv4 address."""
    print_header("Public IPv4 Address")
    ip = get_public_ipv4()
    if ip:
        print_table([["IPv4", Fore.GREEN + ip + Style.RESET_ALL]])


def show_ipv6():
    """Menu option 2 / --ipv6: display the public IPv6 address."""
    print_header("Public IPv6 Address")
    ip = get_public_ipv6()
    if ip:
        print_table([["IPv6", Fore.GREEN + ip + Style.RESET_ALL]])
    else:
        print(Fore.YELLOW + "No public IPv6 address found. Your network or ISP "
              "may not support IPv6.")


def show_full_report():
    """Menu option 3 / --report: display IPv4, IPv6, hostname and details."""
    print_header("Full IP Report")
    report = build_full_report()
    print_table([
        ["Public IPv4", report["public_ipv4"] or "Not available"],
        ["Public IPv6", report["public_ipv6"] or "Not available"],
        ["Hostname", report["hostname"] or "Not available"],
    ], headers=("Address Type", "Address"))
    if report["details"]:
        print("\n" + Fore.CYAN + "Location and provider details:")
        print_table(build_details_rows(report["details"]))


def show_ip_lookup(ip):
    """Validate `ip`, then show its hostname and details (option 4 / --lookup).

    Returns True if the lookup ran, False if the IP was rejected.
    """
    ip = ip.strip()
    if get_ip_version(ip) is None:
        print_error(f"'{ip}' is not a valid IP address.")
        return False
    if not is_public_ip(ip):
        print_error(f"{ip} is a private or reserved address; it has no public "
                    "location data.")
        return False
    details = get_ip_details(ip)
    hostname = get_hostname(ip)
    rows = [["Hostname", hostname or "Not available"]]
    if details:
        rows.extend(build_details_rows(details))
    print_table(rows)
    return True


def lookup_custom_ip():
    """Menu option 4: ask the user for an IP and look it up."""
    print_header("Look Up an IP Address")
    show_ip_lookup(input("Enter an IPv4 or IPv6 address: "))


def save_report(fmt="json"):
    """Menu options 5 and 6 / --save: save the full report as JSON or CSV."""
    print_header(f"Save Report ({fmt.upper()})")
    report = build_full_report()
    try:
        path = write_report(report, fmt)
        print(Fore.GREEN + f"Report saved to {path}")
    except (OSError, ValueError) as err:
        print_error(f"Could not save the file: {err}")


# ---------------------------------------------------------------------------
# Command-line arguments (NEW in v2.0)
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    """Read command-line arguments. With no arguments, the menu is shown.

    Only one option can be used at a time.
    """
    parser = argparse.ArgumentParser(
        description="Show public IP addressing information for network technicians.",
        epilog="Run with no options to open the interactive menu.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ipv4", action="store_true", help="show my public IPv4 address")
    group.add_argument("--ipv6", action="store_true", help="show my public IPv6 address")
    group.add_argument("--report", action="store_true", help="show the full report")
    group.add_argument("--lookup", metavar="IP", help="look up any IPv4 or IPv6 address")
    group.add_argument("--save", choices=REPORT_FORMATS, help="save the full report as json or csv")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def run_cli(args):
    """Run the action chosen on the command line.

    Returns True if an action ran, or False if no option was given
    (so main() opens the menu instead).
    """
    if args.ipv4:
        show_ipv4()
    elif args.ipv6:
        show_ipv6()
    elif args.report:
        show_full_report()
    elif args.lookup:
        print_header("Look Up an IP Address")
        show_ip_lookup(args.lookup)
    elif args.save:
        save_report(args.save)
    else:
        return False
    return True


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------
def main_menu():
    """Print the menu and return the user's choice in lowercase."""
    print_header(f"IP Address Information Tool v{__version__}")
    for key, text in MENU_OPTIONS:
        print(f"  {Fore.YELLOW}{key}{Style.RESET_ALL}) {text}")
    return input("\nChoose an option: ").strip().lower()


def run_menu():
    """Run the interactive menu loop until the user quits."""
    actions = {
        "1": show_ipv4,
        "2": show_ipv6,
        "3": show_full_report,
        "4": lookup_custom_ip,
        "5": lambda: save_report("json"),
        "6": lambda: save_report("csv"),
    }
    while True:
        choice = main_menu()
        if choice in ("q", "quit", "exit"):
            print(Fore.CYAN + "Goodbye!")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print_error("Invalid option. Please choose 1-6 or q.")
        input("\nPress Enter to return to the menu...")


def main(argv=None):
    """Entry point: use command-line options if given, otherwise the menu."""
    args = parse_args(argv)
    if not run_cli(args):
        run_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # User pressed Ctrl+C
        print("\n" + Fore.CYAN + "Goodbye!")
