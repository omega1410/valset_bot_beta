news_state = set()


def add(user_id):
    news_state.add(user_id)


def discard(user_id):
    news_state.discard(user_id)


def has(user_id):
    return user_id in news_state
