from datetime import datetime
from collections import defaultdict

import random
import locale
import baas32

locale.setlocale(locale.LC_TIME, 'nl_NL')

STATUS_EMOJI = {
    'Niet begonnen': '⏸',
    'Begonnen':      '▶️',
    'Done':          '✅',
    'Niet Done':     '❌'
}

def stranger_message(name):
    return f'''
Heya, {name}! Cool dat je even komt kijken!

Voor nu is deze bot nog even afgesloten voor het publiek, 
maar kom later vooral een keertje terug.

Joe!'''


def me_message(user_id):
    return f'''
Dit weet ik over je:

svia.nl user_id: {user_id}
'''


def tasks_message(tasks, is_group=False, user_name=None):
    groups = defaultdict(list)
    for task in tasks:
        groups[task['group']['id']].append(task)

    if not user_name:
        user_name = 'Je'
    else:
        user_name += '\'s'

    if is_group:
        msg = f'<strong>{user_name} taken voor deze groep:</strong>\n\n'
    else:
        msg = f'<strong>{user_name} taken:</strong>\n\n'

    for _, group_tasks in groups.items():
        if not group_tasks:
            continue

        group_name = group_tasks[0]['group']['name'] if not is_group else None
        msg += taskset_message(group_name, group_tasks)

    random_task = baas32.encode(random.choice(tasks)['id'])
    msg += f'Gebruik /task &lt;task_id&gt; voor meer informatie. ' \
           f'Bijvoorbeeld: /task {random_task}'

    return msg


def taskset_message(name, tasks):
    msg = f'<strong>{name}:</strong>\n' if name else ''
    for task in tasks:
        task_code = baas32.encode(task['id'])
        emoji = STATUS_EMOJI[task['status']]
        if len(task['users']) == 2:
            emoji += ' 👨‍👦'
        elif len(task['users']) == 3:
            emoji += ' 👨‍👧‍👦'
        elif len(task['users']) > 3:
            emoji += ' 👨‍👩‍👧‍👧'

        msg += f'• <code>[{task_code}]</code> ' \
               f'{emoji} {task["title"].strip()}'

        msg += '\n'

    msg += '\n'

    return msg


def task_message(task, is_group):
    task_code = baas32.encode(task['id'])
    msg = f'<code>[{task_code}]</code> <strong>{task["title"]}</strong>\n'

    timestamp = datetime.strptime(task["timestamp"], "%Y-%m-%dT%H:%M:%S")
    msg += f'<em>{timestamp.strftime("%d %B %Y, %H:%M")}</em>\n\n'

    # Print the task group
    msg += f'<strong>Groep:</strong> {task["group"]["name"]}\n'

    # Print the task state
    msg += f'<strong>Status:</strong> {task["status"]}\n'

    # Print task owner(s)
    users = task['users']
    if not users:
        msg += f'<em>Geen eigenaren</em>\n'
    elif len(users) == 1:
        msg += f'<strong>Eigenaar:</strong> {users[0]["name"]}\n'
    elif 1 < len(users) <= 2:
        msg += f'<strong>Eigenaren:</strong> ' \
               f'{users[0]["name"]} en {users[1]["name"]}\n'
    else:
        msg += '\n<strong>Eigenaren:</strong>\n'
        for user in task['users']:
            msg += f'• {user["name"]}\n'
    msg += '\n'

    # Print the description, if available
    try:
        msg += f'<strong>Beschrijving:</strong>\n{task["content"]}\n\n'
    except KeyError:
        pass

    # Print the minute URL, if available
    try:
        minute = task['minute']
        minute_url = f'http://svia.nl/pimpy/minutes/single/{minute["id"]}/'
        minute_url += str(minute['line']) if 'line' in minute else ''

        msg += f'<a href="{minute_url}">Bijbehorende notulen</a>\n'
    except KeyError:
        msg += f'<em>Geen bijbehorende notulen</em>\n'

    keyboard = []
    if task['status'] != 'Niet begonnen':
        keyboard.append({
            'text': '⏸ Niet begonnen',
            'callback_data': f'status unstarted {task["id"]}'
        })
    if task['status'] != 'Begonnen':
        keyboard.append({
            'text': '▶️ Begonnen',
            'callback_data': f'status started {task["id"]}'
        })
    if task['status'] != 'Done':
        keyboard.append({
            'text': '✅ Done',
            'callback_data': f'status done {task["id"]}'
        })
    if task['status'] != 'Niet Done':
        keyboard.append({
            'text': '❌ Niet Done',
            'callback_data': f'status notdone {task["id"]}'
        })

    reply_markup = {'inline_keyboard': [keyboard]}
    return msg, reply_markup
