#!/usr/bin/env python3
"""
Poornima University Exam Cell - Administrator Account Recovery Tool
===================================================================
This CLI utility is for authorized technical administrators to securely recover
or reset administrator credentials on the host server without exposing passwords
in plaintext or exposing public unauthenticated reset endpoints.

Usage:
  Interactive Mode:
    python reset_admin.py

  Direct CLI Arguments:
    python reset_admin.py --username admin --password "NewSecurePass123"

  Generate Emergency Recovery Key:
    python reset_admin.py --generate-key
"""

import sys
import os
import json
import argparse
import getpass
import secrets
from werkzeug.security import generate_password_hash

USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')
RECOVERY_KEY_FILE = os.path.join(os.path.dirname(__file__), 'admin_recovery.key')


def read_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception as e:
        print(f"[Error] Failed to read {USERS_FILE}: {e}")
        return []


def write_users(users):
    try:
        temp_file = USERS_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
        os.replace(temp_file, USERS_FILE)
        return True
    except Exception as e:
        print(f"[Error] Failed to write {USERS_FILE}: {e}")
        return False


def generate_recovery_key():
    token = secrets.token_urlsafe(32)
    with open(RECOVERY_KEY_FILE, 'w', encoding='utf-8') as f:
        f.write(token.strip())
    print("\n" + "=" * 60)
    print("NEW EMERGENCY RECOVERY KEY GENERATED")
    print("=" * 60)
    print(f"Key: {token}")
    print(f"Saved to: {RECOVERY_KEY_FILE}")
    print("Keep this key strictly confidential for authorized IT staff.")
    print("=" * 60 + "\n")
    return token


def reset_password(username, new_password):
    if not username:
        print("[Error] Username cannot be empty.")
        return False
    if not new_password or len(new_password) < 6:
        print("[Error] Password must be at least 6 characters long.")
        return False

    users = read_users()
    hashed = generate_password_hash(new_password)

    found = False
    for user in users:
        if isinstance(user, dict) and user.get('username') == username:
            user['password'] = hashed
            found = True
            break

    if not found:
        # Create user if it doesn't exist
        users.append({
            'username': username,
            'password': hashed
        })

    if write_users(users):
        print("\n" + "=" * 60)
        print(f"SUCCESS: Password for user '{username}' has been securely reset.")
        print("Password has been stored with modern cryptographic hash.")
        print("=" * 60 + "\n")
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Poornima University Exam Cell Admin Recovery Tool")
    parser.add_argument('--username', '-u', help="Admin username to reset")
    parser.add_argument('--password', '-p', help="New password for the admin")
    parser.add_argument('--generate-key', action='store_true', help="Generate a new emergency recovery key")

    args = parser.parse_args()

    if args.generate_key:
        generate_recovery_key()
        return

    username = args.username
    password = args.password

    if not username or not password:
        print("\n" + "=" * 60)
        print("Poornima University Exam Cell - Admin Password Reset Utility")
        print("=" * 60)

        if not username:
            username = input("Enter admin username [default: admin]: ").strip() or "admin"

        if not password:
            while True:
                p1 = getpass.getpass("Enter new password (min 6 characters): ")
                if len(p1) < 6:
                    print("Password too short. Minimum 6 characters required.")
                    continue
                p2 = getpass.getpass("Confirm new password: ")
                if p1 != p2:
                    print("Passwords do not match. Try again.")
                    continue
                password = p1
                break

    reset_password(username, password)


if __name__ == '__main__':
    main()
