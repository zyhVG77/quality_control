from base64 import b64encode, b64decode
from functools import wraps
from user.util.utils import TOKENTIMEOUT,DEBUG
from user.models import *
import random
import time
import json

# ////////////////////////////////////////////////////////////
# token相关
# ////////////////////////////////////////////////////////////

userTokens = {}


class userStatus():
    def __init__(self, user, token, timeout):
        self.user = user
        self.token = token
        self.timeout = timeout


def verify_decorator(verify: bool = True):
    def new_decorator(func):
        @wraps(func)
        def decorated(request, **kwargs):
            try:
                if request.method == 'POST':
                    # payload is json-like
                    kwargs.update(json.loads(request.body.decode()))

                elif request.method == 'GET':
                    kwargs.update(request.GET)
                # todo: for return render in someplaces
                kwargs['request'] = request
                if verify:
                    kwargs['user'] = _verifyToken(request.headers['Authentication'])
                return func(**kwargs)
            except Exception as e:
                raise e
                # todo: unmark these codes
                # return {
                #     'status': 'fail',
                #     'error_message': str(e)
                # }

        return decorated

    return new_decorator


def _getToken(user: user_account_info, withoutTimeout=True):
    token = b64encode(":".join([str(user.uid),
                                str(user.name),
                                str(random.random()),
                                ]).encode()).decode()
    userTokens[user.uid] = userStatus(user, token, -1 if withoutTimeout else time.time() + TOKENTIMEOUT)

    if DEBUG:
        print('Id:' + user.uid)
        print('Token:' + token)

    return token


def _verifyToken(token):
    tmpTime = time.time()

    _token = b64decode(token).decode()
    userId = _token.split(':')[0]

    if not userId in userTokens:
        raise Exception('user not login')
    elif userTokens[userId].token != token:
        raise Exception('invalid token')
    elif userTokens[userId].timeout == -1:
        if DEBUG:
            print('\nAlter workshop')
            print('---------------------------------------')
            print('Id:' + userId)
            print('validateTime:' + str(userTokens[userId].timeout) + '->' + str(userTokens[userId].timeout))
        return userTokens[userId].user
    elif tmpTime > userTokens[userId].timeout:
        raise Exception('timeout please login')
    else:
        if DEBUG:
            print('Id:' + userId)
            print('validateTime:' + str(userTokens[userId].timeout) + '->' + str(tmpTime + TOKENTIMEOUT))
        userTokens[userId].timeout = tmpTime + TOKENTIMEOUT
        return userTokens[userId].user


# ////////////////////////////////////////////////////////////
# 用户接口相关
# ////////////////////////////////////////////////////////////

@verify_decorator(False)
def confirmLogin(username=None, password=None, rememberMe=False, **kwargs):
    try:
        user = user_account_info.objects.get(name=username)
        # todo: enable password verify
        # if user.password_hash != password:
        #     raise Exception("incorrect password")
        response = {
            'user': {
                'id': user.uid,
                'username': user.name,
                'email': user.user_info.email,
                'fullname': user.user_info.fullname,
                'work_id': user.user_info.work_id,
                'phone': user.user_info.phone,
                'avatar': user.user_info.avatar,
                'role': user.get_role_display(),
            },
            'status': 'success',
            'token': _getToken(user, rememberMe)
        }
        return response
    except Exception as e:
        return {
            'status': 'fail',
            'error_message': str(e)
        }


@verify_decorator()
def getUserInfo(user: user_account_info = None, **kwargs):
    response = {
        'status': 'success',
        'user': {
            'id': user.uid,
            'username': user.name,
            'email': user.user_info.email,
            'fullname': user.user_info.fullname,
            'phone': user.user_info.work_id,
            'workId': user.user_info.work_id,
            'avatar': user.user_info.avatar,
            'role': user.get_role_display()
        }
    }
    return response


@verify_decorator()
def updateUserInfo(user: user_account_info = None, **kwargs):
    userId = kwargs.pop('id')
    if user.role != RoleChoices.SUPEREDITOR and user.uid != userId:
        raise Exception('unauthorized operation')

    # todo: considering if update role-like kwargs
    userInfo = None
    try:
        userInfo = user_account_info.objects.get(uid=userId).user_info
        if 'avatar' in kwargs:
            userInfo.avatar = kwargs.pop('avatar')
        if 'email' in kwargs:
            userInfo.email = kwargs.pop('email')
        if 'fullname' in kwargs:
            userInfo.fullname = kwargs.pop('fullname')
        if 'phone' in kwargs:
            userInfo.phone = kwargs.pop('phone')
        if 'workId' in kwargs:
            userInfo.work_id = kwargs.pop('workId')
        userInfo.save()
        response = {
            'status': 'success',
            'id': userId,
            'avatar': userInfo.avatar,
            'email': userInfo.email,
            'fullname': userInfo.fullname,
            'phone': userInfo.phone,
            'role': kwargs.pop('role'),
            'username': kwargs.pop('username'),
            'workId': userInfo.work_id
        }
        return response
    except Exception as e:
        if not userInfo:
            userInfo = user_account_info.objects.get(uid=userId).user_info
        response = {
            'status': 'fail',
            'error_message': str(e),
            'id': userId,
            'avatar': userInfo.avatar,
            'email': userInfo.email,
            'fullname': userInfo.fullname,
            'phone': userInfo.phone,
            'role': kwargs.pop('role'),
            'username': kwargs.pop('username'),
            'workId': userInfo.work_id
        }
        return response