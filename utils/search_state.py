search_state = set()

def add(user_id):
    search_state.add(user_id)
def remove(user_id):
    search_state.discard(user_id)
def has(user_id):
    return user_id in search_state
