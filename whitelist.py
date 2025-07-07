WHITELIST_FILE = "whitelist.txt"


def is_user_allowed(user_id: int) -> bool:
    try:
        with open(WHITELIST_FILE, "r") as f:
            return str(user_id) in f.read().splitlines()
    except FileNotFoundError:
        return False


def add_user_to_whitelist(user_id: int) -> bool:
    if is_user_allowed(user_id):
        return False 

    with open(WHITELIST_FILE, "a") as f:
        f.write(f"{user_id}\n")
    return True
