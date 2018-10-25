# chat/views.py
import time
import json
import requests
import uuid
import datetime
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from chat.models import User, Group, GroupChat, ImageModel

res = {
		'code': -1,
		'msg': '',
		'data': {
		}
	}


def home(request):
	user_id = request.GET.get('user_id', None)
	if user_id is not None:
		user = User.objects.get(id=user_id)
		return render(request, 'chat.html', {'id': user_id})
	return render(request, 'chat.html', {'user_id': user_id})


@csrf_exempt
def msg_gateway(request):
	'''
	接收客户端发送的消息
	:param request:
	:return:
	'''
	if request.method == 'POST':
		# print(request.POST)
		from_user_name = request.POST.get('mine[username]', None)
		from_user_avatar = request.POST.get('mine[avatar]', None)
		from_user_id = request.POST.get('mine[id]', None)
		content = request.POST.get('mine[content]', None)
		
		# 消息接收方
		to_user = request.POST.get('to[name]', None)
		# 好友类型
		user_type = request.POST.get('to[type]', None)
		# 如果是群聊里的消息，这个是群聊的ID
		# 如果是私聊的消息，则是对方的ID
		to_user_id = request.POST.get('to[id]', None)
		# msg中的id字段表示的消息来源ID
		# 如果是群聊消息则是to_user_id
		# 如果是私聊消息则是from_user_id
		id_ = from_user_id
		mine = False
		if 'group' == user_type:
			id_ = to_user_id
			# mine = True
		msg = {
			# 消息来源用户名
			'username': from_user_name,
			# 消息来源用户头像
			'avatar': from_user_avatar,
			# 消息的来源ID（如果是私聊，则是用户id，如果是群聊，则是群组id）
			'id': id_,
			'type': user_type,
			'content': content,
			# 消息id，可不传。除非你要对消息进行一些操作（如撤回）
			'cid': 0,
			# 是否我发送的消息，如果为true，则会显示在右方
			'mine': mine,
			# 消息的发送者id（比如群组中的某个消息发送者），可用于自动解决浏览器多窗口时的一些问题
			'fromid': from_user_id,
			'timestamp': int(time.time() * 1000),
		}
		content = {
			'type': 'msg',
			'msg': msg,
		}
		publish(to_user_id, json.dumps(content))
		return JsonResponse({'code': 0, 'status': True, 'info': '消息发送成功'})


def publish(channel, content):
	'''
	:param msg:
	:return:
	'''
	url = 'http://rest-hangzhou.goeasy.io/publish'
	appkey = 'BC-88d728e1914144a893e8e438a1095518'
	data = dict(
		appkey=appkey,
		channel=channel,
		content=content,
	)
	r = requests.post(url, data=data)
	print(r.json())
	code = r.json().get('code', None)
	if code == 200:
		return True
	return False


def init_user(request):
	'''
	初始化用户聊天界面
	:param request:
	:return:
	'''
	res = {
		'code': -1,
		'msg': '初始化',
		'data': {
			'mine': {
			
			},
			'friend': [
			
			],
			'group': [
			
			]
		}
	}
	user_id = request.GET.get('user_id', None)
	# print('user_id', user_id)
	if user_id is None:
		res['msg'] = 'user_id is None'
		return JsonResponse(res)
	
	# 查询用户的好友分组
	groups = Group.objects.filter(owner=user_id)
	friends = list()
	for item in groups:
		# print('group', item.name)
		friend_list = [{'username': fri.username, 'id': fri.id, 'avatar': fri.avatar, 'sign': fri.signature, 'status': fri.status}
					 for fri in item.group_members.all()]
		group_friends = {
			'groupname': item.name,
			'id': item.id,
			'list': friend_list,
		}
		friends.append(group_friends)
	
	# 好友列表
	res['data']['friend'] = friends
	
	# 群组列表
	user = User.objects.get(pk=user_id)
	group_chats = user.groupchat_set.all()
	res['data']['group'] = [{'groupname': item.name, 'id': item.id, 'avatar': item.group_chat_avatar} for item in group_chats]
	
	# 我的信息
	res['data']['mine'] = {
		'username': user.username,
		'id': user.id,
		'status': 'online',
		'sign': user.signature,
		'avatar': user.avatar,
	}
	res['code'] = 0
	return JsonResponse(res)


def init_group_chat(request):
	'''
	获取用户群聊信息
	:param request:
	:return:
	'''
	# 获取layim框架传递的群聊ID
	group_chat_id = request.GET.get('id', None)
	res = {
		'code': 0,
		'msg': '',
		'data': {
			'list': [
			
			]
		}
	}
	if group_chat_id is None:
		res['msg'] = 'group_chat_id is None'
		return JsonResponse(res)
	group_chat = GroupChat.objects.get(id=group_chat_id)
	res['data']['list'] = [
					{
						'username': item.username,
						'id': item.id,
						'avatar': item.avatar,
						'sign': item.signature
					}
					for item in group_chat.group_chat_members.all()
	]
	
	return JsonResponse(res)


@csrf_exempt
def add_friend(request):
	'''
	添加好友
	:param request:
	:return:
	'''
	res_type = request.POST.get('res_type', None)
	# 用户A申请添加用户B为好友
	if 'add' == res_type:
		# 申请添加好友的用户ID
		a_user_id = request.POST.get('user_id', None)
		# 被添加的用户ID
		b_friend_id = request.POST.get('friend_id', None)
		# 目标好友组
		to_group_id = request.POST.get('to_group_id', None)
		# 好友申请信息
		remark = request.POST.get('remark', None)
		print('用户A的ID', a_user_id)
		user = User.objects.get(pk=a_user_id)
		friend = User.objects.get(pk=b_friend_id)
		print('%s要添加%s为好友' % (user.username, friend.username))
		# 向用户B发送好友申请
		content = {
			'type': 'friend',
			'msg': {
				'type': 'friend',
				'username': user.username,
				'avatar': user.avatar,
				'from_user_id': a_user_id,
				'id': a_user_id,
				'to_group_id': to_group_id,
				# 'groupid': to_group_id,
				# 'sign': user.signature,
			},
		}
		publish('%sbe_added_as_a_friend' % b_friend_id, json.dumps(content))
		return JsonResponse({'code': 0, 'status': True, 'info': '好友申请已发送'})
	# 用户B同意用户A的好友申请
	elif 'pass' == res_type:
		# 申请添加好友的用户ID
		user_id = request.POST.get('user_id', None)
		user = User.objects.get(id=user_id)
		# 被添加的用户ID
		friend_id = request.POST.get('friend_id', None)
		# 用户A的好友组
		a_group_id = request.POST.get('a_group_id', None)
		# 用户B的好友组
		b_group_id = request.POST.get('b_group_id', None)
		
		friend = User.objects.get(id=friend_id)
		# 获取好友组
		a_group = Group.objects.get(id=a_group_id)
		a_group.group_members.add(friend)
		b_group = Group.objects.get(pk=b_group_id)
		b_group.group_members.add(user)
		print('%s同意了%s的好友申请' % (friend.username, user.username))
		# 向用户A通知申请通过
		a_content = {
			'type': 'pass',
			'msg': {
				'type': 'friend',
				'avatar': friend.avatar,
				'username': friend.username,
				'groupid': a_group_id,
				'id': friend_id,
				'sign': friend.signature,
			},
		}
		
		b_content = {
			'type': 'pass',
			'msg': {
				'type': 'friend',
				'avatar': user.avatar,
				'username': user.username,
				'groupid': b_group_id,
				'id': user_id,
				'sign': user.signature,
			},
		}
		publish('%sfriend_result' % user_id, json.dumps(a_content))
		return JsonResponse(b_content['msg'])


@csrf_exempt
def search_friend(request):
	'''
	搜索好友
	:param request:
	:return:
	'''
	res = {
		'code': 0,
		'msg': '',
		'count': 0,
		'data': []
	}
	if request.method == 'POST':
		key_word = request.POST.get('key_word', None)
		if key_word is None:
			res['code'] = -1
			res['msg'] = 'kew_word is none'
			return JsonResponse(res)
		result = [{'username': user.username, 'id': user.id, 'sex': user.sex, 'sign': user.signature, 'avatar': user.avatar}
				  for user in User.objects.filter(username__icontains=key_word)]
		res['count'] = len(result)
		res['data'] = result
		return JsonResponse(res)


@csrf_exempt
def upload_image(request):
	'''
	上传图片
	:param request:
	:return:
	'''
	if request.method == 'POST':
		pic = request.FILES.get('file')
		pic.name = str(uuid.uuid4()) + pic.name
		image = ImageModel.objects.create(model_pic=pic)
		# qiniu_upload(pic)
		print(image.model_pic.name)
		res['code'] = 0
		date = datetime.datetime.now().strftime("%y%m%d")
		res['data']['src'] = '%s/statics/upload/%s/%s' % ('http://127.0.0.1:8000', date, pic.name)
		print(res)
		return JsonResponse(res)
	res['msg'] = '上传文件失败'
	return JsonResponse(res)


@csrf_exempt
def modify_sign(request):
	'''
	用户修改签名
	:param request:
	:return:
	'''
	if request.method == 'POST':
		sign = request.POST.get('sign', None)
		user_id = request.POST.get('id', None)
		print('sign', sign)
		print('user_id', user_id)
		if sign and user_id:
			user = User.objects.get(pk=user_id)
			user.signature = sign
			user.save()
			return JsonResponse({'code': 0, 'msg': 'success'})
		return JsonResponse({'code': -1, 'msg': 'invalid parameters'})
	

@csrf_exempt
def group_chat_ids(request):
	if request.method == 'POST':
		user_id = request.POST.get('user_id', None)
		if not user_id:
			return JsonResponse({'code': -1, 'msg': 'invalid parameters'})
		user = User.objects.get(pk=user_id)
		group_chats = user.groupchat_set.all()
		data = [item.id for item in group_chats]
		return JsonResponse({'code': 0, 'msg': '', 'data': data})
