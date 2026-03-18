import os
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CSV_PATH = os.path.join(BASE_DIR, 'data', 'users.csv')


def init_db():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password', 'display_name'])


def get_all_users():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def register_user(username, password):
    users = get_all_users()
    if any(u['username'] == username for u in users):
        return False

    with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([username, password, username])
    return True


def update_display_name(username, new_name):
    users = get_all_users()
    found = False
    for u in users:
        if u['username'] == username:
            u['display_name'] = new_name
            found = True

    if found:
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f, fieldnames=['username', 'password', 'display_name'])
            writer.writeheader()
            writer.writerows(users)
    return found


def verify_user(username, password):
    users = get_all_users()
    for u in users:
        if u['username'] == username and u['password'] == password:
            return u
    return None
