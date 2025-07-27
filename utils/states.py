# utils/states.py
class UserStates:
    def __init__(self):
        self.states = {}  # user_id -> state
        self.data = {}  # user_id -> additional data

    def set_state(self, user_id, state, data=None):
        self.states[user_id] = state
        if data is not None:
            self.data[user_id] = data

    def get_state(self, user_id):
        return self.states.get(user_id)

    def get_data(self, user_id):
        return self.data.get(user_id)

    def clear_state(self, user_id):
        self.states.pop(user_id, None)
        self.data.pop(user_id, None)
        return True

    def has_state(self, user_id):
        return user_id in self.states


# Глобальный объект состояний
user_states = UserStates()

# Константы состояний
STATE_FEEDBACK = "feedback"
STATE_LOGBOOK_NEW = "logbook_new"
STATE_LOGBOOK_EDIT = "logbook_edit"
STATE_SEARCH = "search"
