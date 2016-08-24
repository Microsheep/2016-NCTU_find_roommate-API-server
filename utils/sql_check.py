def check_safe(text, l):
    danger = ["\"", "\'"]
    kill_danger = ''.join(t if t not in danger else '' for t in text)
    return len(text) >= l and len(text) == len(kill_danger)
