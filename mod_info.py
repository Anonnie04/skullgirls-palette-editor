"""Validate the editable manifest fields accepted by Mod Manager."""
import re


def validate_details(details):
    if not isinstance(details, dict):
        raise ValueError('Enter the mod name, description and version.')
    if any(not isinstance(details.get(key), str) for key in ('name', 'desc', 'version')):
        raise ValueError('Mod details must contain text values.')
    name, version = details['name'].strip(), details['version'].strip()
    if not name or len(name) > 120:
        raise ValueError('Enter a mod name between 1 and 120 characters.')
    if not re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+){0,2}', version) or any(int(part) > 2147483647 for part in version.split('.')):
        raise ValueError('Use a version with 2–4 numeric parts, such as 1.0.0.')
    return dict(name=name, desc=details['desc'], version=version)
