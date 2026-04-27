"""Shared utility functions for generate_site.py and serve.py."""
from datetime import datetime

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def fmt_date(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except Exception:
        return iso or ''


def fmt_datetime(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y %H:%M')
    except Exception:
        return iso or ''


def iso_to_ymd(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return ''


def month_label(ym):
    y, m = ym.split('-')
    return MONTHS[int(m) - 1] + ' ' + y
