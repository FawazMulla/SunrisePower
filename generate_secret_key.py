#!/usr/bin/env python3
"""
Generate a secure Django secret key for production use.
Run this script and copy the output to your production environment variables.
"""

from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    secret_key = get_random_secret_key()
    print("=" * 60)
    print("DJANGO SECRET KEY FOR PRODUCTION")
    print("=" * 60)
    print(f"SECRET_KEY={secret_key}")
    print("=" * 60)
    print("Copy the SECRET_KEY value above to your production environment variables.")
    print("Keep this key secure and never commit it to version control!")
    print("=" * 60)