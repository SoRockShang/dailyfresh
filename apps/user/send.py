# from celery import Celery
from django.core.mail import send_mail
from django.conf import settings

# app = Celery('celery_tasks',broker='redis://127.0.0.1:6379/6')

# @app.task
def send_register_active_email(to_email, username, token):

    subject = '天天生鲜欢迎您的注册'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击以下链接激活您的账号<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>'%(username, token, token)

    import time
    time.sleep(5)
    send_mail(subject,message,sender,receiver,html_message=html_message)