import urllib.parse
import aiohttp

from config import VIA_HOST, VIA_SCHEME


class ApiError(Exception): pass

class BadRequestError(ApiError): pass
class PermissionDeniedError(ApiError): pass
class NotFoundError(ApiError): pass
class InternalServerError(ApiError): pass


def build_url(path, query_args=None):
    query = urllib.parse.urlencode(query_args if query_args else {})
    parse_result = urllib.parse.ParseResult(
        scheme=VIA_SCHEME, netloc=VIA_HOST, path=path,
        params='', query=query, fragment='')
    return urllib.parse.urlunparse(parse_result)

def check_status(status):
    if status == 400:
        raise BadRequestError
    elif status == 403:
        raise PermissionDeniedError
    elif status == 404:
        raise NotFoundError
    elif status == 500:
        raise InternalServerError


async def get_json(url, token=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            check_status(resp.status)
            return await resp.json()


async def post_json(url, obj, token=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=obj, headers=headers) as resp:
            check_status(resp.status)
            return await resp.json()


async def put_json(url, obj, token=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=obj, headers=headers) as resp:
            check_status(resp.status)
            return await resp.json()


async def get_tasks(token, group_id=None):
    args = {'group_id': group_id} if group_id else {}
    url = build_url('/pimpy/api/tasks/', args)
    return await get_json(url, token=token)


async def get_group_tasks(token, group_id):
    url = build_url(f'/pimpy/api/groups/{group_id:d}/tasks/')
    return await get_json(url, token=token)


async def get_group_user_tasks(token, group_id, user_id='me'):
    url = build_url(f'/pimpy/api/groups/{group_id:d}/users/{user_id}/tasks/')
    return await get_json(url, token=token)


async def get_group_task(token, group_id, task_id):
    url = build_url(f'/pimpy/api/groups/{group_id:d}/tasks/{task_id:d}/')
    return await get_json(url, token=token)


async def add_group_task(token, group_id, owners, title):
    url = build_url(f'/pimpy/api/groups/{group_id:d}/tasks/')
    obj = {'owners': owners, 'title': title}
    return await post_json(url, obj, token=token)


async def get_group_users(token, group_id):
    url = build_url(f'/pimpy/api/groups/{group_id:d}/users/')
    return await get_json(url, token=token)


async def get_task(token, task_id):
    url = build_url(f'/pimpy/api/tasks/{task_id:d}/')
    return await get_json(url, token=token)


async def set_group_task_status(token, group_id, task_id, status):
    url = build_url(f'/pimpy/api/groups/{group_id:d}/tasks/{task_id:d}/status/')
    return await put_json(url, {'status': status}, token=token)


async def set_task_status(token, task_id, status):
    url = build_url(f'/pimpy/api/tasks/{task_id:d}/status/')
    return await put_json(url, {'status': status}, token=token)
