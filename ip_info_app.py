"""
IP Address Information Application
==================================
DEVASC Project - Option 2: IPv4/IPv6 Address Application

Purpose:
    A command-line tool for network technicians that shows the computer's
    current public IPv4 and IPv6 addresses, plus geolocation and provider
    details (ISP, ASN, country, etc.) for any IP address.

APIs used (all free, no API key required):
    - ipify IPv4 : https://api.ipify.org?format=json
    - ipify IPv6 : https://api64.ipify.org?format=json
                   (returns IPv6 if available, otherwise falls back to IPv4)
    - ipapi.co   : https://ipapi.co/<ip>/json/
                   (location, ISP, ASN; free tier is about 1,000 requests/day)

How to run:
    pip install -r requirements.txt
    python ip_info_app.py

How to extend (for future teams):
    - Each API call lives in its own function (get_public_ipv4, get_public_ipv6,
      get_ip_details). To switch providers, change only that function.
    - To show more fields, add entries to DETAIL_FIELDS below.
    - To add a menu option, add a line in MENU_OPTIONS and a branch in main().
"""

import ipaddress
import json
from datetime import datetime

import requests
from colorama import Fore, Style, init
from tabulate import tabulate

# Make colors work on Windows terminals too; reset color after each print.
init(autoreset=True)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
IPV4_URL = "https://api.ipify.org?format=json"
IPV6_URL = "https://api64.ipify.org?format=json"
DETAILS_URL = "https://ipapi.co/{ip}/json/"
TIMEOUT_SECONDS = 10  # Stop waiting for an API after this many seconds

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
                                headers={"User-Agent": "devasc-ip-info-app/1.0"})
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
    """Menu option 1: display the public IPv4 address."""
    print_header("Public IPv4 Address")
    ip = get_public_ipv4()
    if ip:
        print_table([["IPv4", Fore.GREEN + ip + Style.RESET_ALL]])


def show_ipv6():
    """Menu option 2: display the public IPv6 address."""
    print_header("Public IPv6 Address")
    ip = get_public_ipv6()
    if ip:
        print_table([["IPv6", Fore.GREEN + ip + Style.RESET_ALL]])
    else:
        print(Fore.YELLOW + "No public IPv6 address found. Your network or ISP "
              "may not support IPv6.")


def build_full_report():
    """Collect IPv4, IPv6 and details into one dict (used by options 3 and 5)."""
    ipv4 = get_public_ipv4()
    ipv6 = get_public_ipv6()
    details = get_ip_details(ipv4 or ipv6 or "")
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "public_ipv4": ipv4,
        "public_ipv6": ipv6,
        "details": details,
    }


def show_full_report():
    """Menu option 3: display IPv4, IPv6 and location/ISP details."""
    print_header("Full IP Report")
    report = build_full_report()
    print_table([
        ["Public IPv4", report["public_ipv4"] or "Not available"],
        ["Public IPv6", report["public_ipv6"] or "Not available"],
    ], headers=("Address Type", "Address"))
    if report["details"]:
        print("\n" + Fore.CYAN + "Location and provider details:")
        print_table(build_details_rows(report["details"]))


def lookup_custom_ip():
    """Menu option 4: ask for an IP, validate it, and show its details."""
    print_header("Look Up an IP Address")
    ip = input("Enter an IPv4 or IPv6 address: ").strip()
    version = get_ip_version(ip)
    if version is None:
        print_error(f"'{ip}' is not a valid IP address.")
        return
    if not is_public_ip(ip):
        print_error(f"{ip} is a private or reserved address; it has no public "
                    "location data.")
        return
    details = get_ip_details(ip)
    if details:
        print_table(build_details_rows(details))


def save_report():
    """Menu option 5: save the full report to a timestamped JSON file."""
    print_header("Save Report")
    report = build_full_report()
    filename = f"ip_report_{datetime.now():%Y%m%d_%H%M%S}.json"
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4)
        print(Fore.GREEN + f"Report saved to {filename}")
    except OSError as err:
        print_error(f"Could not save the file: {err}")


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------
def main_menu():
    """Print the menu and return the user's choice in lowercase."""
    print_header("IP Address Information Tool")
    for key, text in MENU_OPTIONS:
        print(f"  {Fore.YELLOW}{key}{Style.RESET_ALL}) {text}")
    return input("\nChoose an option: ").strip().lower()


def main():
    """Run the menu loop until the user quits."""
    actions = {
        "1": show_ipv4,
        "2": show_ipv6,
        "3": show_full_report,
        "4": lookup_custom_ip,
        "5": save_report,
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
            print_error("Invalid option. Please choose 1-5 or q.")
        input("\nPress Enter to return to the menu...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # User pressed Ctrl+C
        print("\n" + Fore.CYAN + "Goodbye!")
