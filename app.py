#!/usr/bin/env python3
import json
import re
from collections import defaultdict
from math import ceil

import baas32
import telewalrus.bot

import api
import messages


from config import VIA_GROUPS, TG_TOKEN, USER_TOKENS
BOT = telewalrus.bot.Bot(TG_TOKEN)


class Database:
    user_tokens = {}
    group_ids = {}

    @staticmethod
    def load():
        try:
            f = open('database.json', 'r')
        except OSError:
            print('database does not exist, generating from config')
            Database.user_tokens = USER_TOKENS
            Database.group_ids = VIA_GROUPS
            return

        database = json.load(f)

        Database.user_tokens = database.get('user_tokens') or USER_TOKENS
        Database.group_ids = database.get('group_ids') or VIA_GROUPS

    @staticmethod
    def save():
        database = {
            'user_tokens': Database.user_tokens,
            'group_ids': Database.group_ids
        }
        with open('database.json', 'w') as f:
            json.dump(database, f, indent=4)


@BOT.command('start')
async def cmd_start(message):
    name = message.from_user.first_name
    if str(message.from_user.id) in Database.user_tokens:
        await message.chat.message(
            f'Welkom terug, {name}! Zie /tasks om te zien welke taken je open '
            f'hebt staan.')
        return

    token = message.args.strip()
    if not token:
        await message.chat.message(
            f'Hee hallo, {name}! Ik draai nog met de acceptatieversie van de via-site. '
            f'Wil je me alsnog testen? Vraag dan even aan @sijman '
            f'of hij je je API token wil geven. Dan kan je meteen aan de slag!')
        return

    try:
        await api.test_token(token)
    except api.PermissionDeniedError:
        await message.chat.message(
            f'Hallo, {name}! Helaas is dat geen geldige API token...')

    Database.user_tokens[str(message.from_user.id)] = token
    await message.chat.message(
        f'Welkom, {name}! Zie /tasks om te zien welke taken je open hebt '
        f'staan.')


@BOT.command('chatinfo')
async def cmd_chatinfo(message):
    chat = message.chat

    if message.chat.type == 'private':
        admins = []
    else:
        admins = [admin.user for admin in await chat.administrators()]

    msg = f'''
id: {chat.id}
type: {chat.type}
title: {chat.title}
username: {chat.username}
first_name: {chat.first_name}
last_name: {chat.last_name}
admins: {admins}
    '''
    await message.chat.message(msg)


@BOT.command('tasks')
async def cmd_tasks(message):
    token = Database.user_tokens.get(str(message.from_user.id))
    if not token:
        msg = messages.stranger_message(message.from_user.first_name)
        await message.chat.message(msg)
        return

    is_group = message.chat.type != 'private'
    if not is_group:
        tasks = await api.get_tasks(token)
        if not tasks:
            await message.chat.message('Je hebt geen taken!')
            return
    else:
        group_id = Database.group_ids.get(str(message.chat.id))
        if group_id is None:
            await message.chat.message(
                'pimpy is nog niet ingeschakeld voor deze groep :/')
            return

        tasks = await api.get_group_user_tasks(token, group_id)
        if not tasks:
            await message.chat.message('Je hebt geen taken voor deze groep!')
            return

    msg = messages.tasks_message(tasks, is_group)
    await message.chat.message(msg, parse_mode='HTML')


@BOT.command('grouptasks')
async def cmd_grouptasks(message):
    token = Database.user_tokens.get(str(message.from_user.id))
    if not token:
        msg = messages.stranger_message(message.from_user.first_name)
        await message.chat.message(msg)
        return

    if message.chat.type == 'private':
        await message.chat.message(
            'Dit commando werkt alleen in commissiechats.')
        return

    group_id = Database.group_ids.get(str(message.chat.id))
    if not group_id:
        await message.chat.message(
            'pimpy is nog niet ingeschakeld voor deze groep :/')
        return

    user_tasks = await api.get_group_tasks(token, group_id)

    msg = ''
    for i, (name, tasks) in enumerate(user_tasks.items()):
        status = defaultdict(int)
        for task in tasks:
            status[task['status']] += 1

        msg += f'<b>{name}</b>:\n' \
               f'    ⏸ {status["Niet begonnen"]}, ▶️ {status["Begonnen"]}, ' \
               f'✅ {status["Done"]}, ❌ {status["Niet Done"]}\n'

    users = await api.get_group_users(token, group_id)
    keyboard = []
    for i, user in enumerate(users):
        if i % 3 == 0:
            keyboard.append([])

        keyboard[-1].append({
            'text': user['name'],
            'callback_data': f'tasks {user["id"]} {user["name"]}'
        })

    msg += '\nKlik op een naam hieronder om zijn/haar taken weer te geven.'
    reply_markup = {'inline_keyboard': keyboard}

    await message.chat.message(msg, parse_mode='HTML',
                               disable_web_page_preview=True,
                               reply_markup=json.dumps(reply_markup))


async def get_task_from_args(token, message, group_id=None):
    task_code = baas32.normalize(message.args) if message.args else ''
    if not task_code:
        await message.chat.message(
            'Welke taak? Protip: zet de taakcode achter het commando.')
        return

    try:
        task_id = baas32.decode(task_code)
    except ValueError:
        await message.chat.message(f'{task_code} is geen geldige taakcode.')
        return

    try:
        if group_id:
            task = await api.get_group_task(token, group_id, task_id)
        else:
            task = await api.get_task(token, task_id)
    except api.NotFoundError:
        await message.chat.message(f'Kan taak {task_code} niet vinden :(')
        return
    except api.PermissionDeniedError:
        await message.chat.message(
            f'Je hebt geen rechten voor taak {task_code}.')
        return

    return task, task_code


@BOT.command('task')
async def cmd_task(message):
    token = Database.user_tokens.get(str(message.from_user.id))
    if not token:
        msg = messages.stranger_message(message.from_user.first_name)
        await message.chat.message(msg)
        return

    group_id = None
    if message.chat.type != 'private':
        group_id = Database.group_ids.get(str(message.chat.id))
        if not group_id:
            await message.chat.message(
                'pimpy is nog niet ingeschakeld voor deze groep :/')
            return

    task, _ = await get_task_from_args(token, message, group_id)
    if not task:
        return

    msg, reply_markup = messages.task_message(task, group_id is not None)

    await message.chat.message(msg, parse_mode='HTML',
                               reply_markup=json.dumps(reply_markup),
                               disable_web_page_preview=True)


@BOT.command('done')
async def cmd_done(message):
    token = Database.user_tokens.get(str(message.from_user.id))
    if not token:
        msg = messages.stranger_message(message.from_user.first_name)
        await message.chat.message(msg)
        return

    group_id = None
    if message.chat.type != 'private':
        group_id = Database.group_ids.get(str(message.chat.id))
        if not group_id:
            await message.chat.message(
                'pimpy is nog niet ingeschakeld voor deze groep :/')
            return

    task, task_code = await get_task_from_args(token, message, group_id)
    if not task:
        return

    try:
        await api.set_task_status(token, task['id'], 'done')
    except api.PermissionDeniedError:
        msg = f'Je mag taak <code>[{task_code}]</code> niet aanpassen!'
        await message.chat.message(msg, parse_mode='HTML')
        return

    msg = f'Taak {task_code} staat nu op done!'
    await message.chat.message(msg)


@BOT.command('actie')
async def cmd_actie(message):
    token = Database.user_tokens.get(str(message.from_user.id))
    if not token:
        msg = messages.stranger_message(message.from_user.first_name)
        await message.chat.message(msg)
        return

    if message.chat.type == 'private':
        await message.chat.message(
            'Deze functie werkt alleen in commissiechats.')
        return

    group_id = Database.group_ids.get(str(message.chat.id))
    if not group_id:
        await message.chat.message(
            'pimpy is nog niet ingeschakeld voor deze groep :/')
        return

    match = re.match(r'^([^:]+): (.*)$', message.args)
    if not match:
        match = re.match(r'^([^ ]+) (.*)$', message.args)
        if match:
            owner = match.group(1)
            title = match.group(2)
            await message.chat.message(
                f'Incorrecte syntax. Misschien bedoelde je /actie {owner}: {title}?')
        else:
            await message.chat.message(
                f'Incorrecte syntax. Probeer eens /actie [naam]: [titel].')

        return

    task = await api.add_group_task(
        token, group_id, match.group(1), match.group(2))
    msg, reply_markup = messages.task_message(task, True)
    task_code = baas32.encode(task['id'])
    msg = f'Taak <code>[{task_code}]</code> aangemaakt!\n\n' + msg

    await message.chat.message(msg, parse_mode='HTML',
                               reply_markup=json.dumps(reply_markup),
                               disable_web_page_preview=True)


async def callback_status(query, _, args):
    await query.answer()

    token = Database.user_tokens.get(str(query.from_user.id))
    if not token:
        msg = messages.stranger_message(message.from_user.first_name)
        await message.chat.message(msg)
        return

    status, task_id = args
    task_id = int(task_id)

    if query.message.chat.type == 'private':
        await api.set_task_status(token, task_id, status)
        task = await api.get_task(token, task_id)
    else:
        group_id = VIA_GROUPS.get(query.message.chat.id)
        if not group_id:
            return

        await api.set_group_task_status(token, group_id, task_id, status)
        task = await api.get_group_task(token, group_id, task_id)

    
    msg, reply_markup = messages.task_message(task, False)
    await query.message.edit(msg, parse_mode='HTML',
                             reply_markup=json.dumps(reply_markup),
                             disable_web_page_preview=True)


async def callback_tasks(query, _, args):
    await query.answer()

    token = Database.user_tokens.get(str(query.from_user.id))
    if not token:
        msg = messages.stranger_message(message.from_user.first_name)
        await message.chat.message(msg)
        return

    group_id = VIA_GROUPS.get(query.message.chat.id)
    if not group_id:
        return

    user_id = int(args[0])
    user_name = ' '.join(args[1:])

    tasks = await api.get_group_user_tasks(token, group_id, user_id)
    msg = messages.tasks_message(tasks, True, user_name)
    await query.message.chat.message(msg, parse_mode='HTML',
                                     disable_web_page_preview=True)


CALLBACK_HANDLERS = {
    'status': callback_status,
    'tasks': callback_tasks
}

@BOT.callback
async def callback(query):
    command, *args = query.data.split(' ')
    handler = CALLBACK_HANDLERS.get(command)
    if handler:
        await handler(query, command, args)


Database.load()
while True:
    try:
        BOT.run()
    except KeyboardInterrupt:
        print('\nsaving database')
        Database.save()
        print('hee doei hè')
        break
    except:
        pass
