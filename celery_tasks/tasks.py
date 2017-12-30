# 使用celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader, RequestContext
from celery import Celery

# 初始化django运行所依赖的环境
# 这几句代码需要在celery worker的一端加上
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
django.setup()

from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

# 创建一个Celery类的对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.49.129/8')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击以下链接激活您的账号<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
        username, token, token)

    # 发送邮件
    # 模拟send_mail函数发邮件执行了5s
    # import time
    # time.sleep(5)
    send_mail(subject, message, sender, receiver, html_message=html_message)


@app.task
def generate_static_index_html():
    '''生成首页静态页面'''
    # 获取商品的分类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品的信息
    index_banner = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    # type_banner = IndexTypeGoodsBanner.objects.all()
    for type in types:
        # 查询首页展示的type类型的文字商品信息
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
        # 查询首页展示的type类型的图片商品信息
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 动态给type对象增加属性title_banner, image_banner
        # 分别保存和type相关的文字商品的信息和图片商品信息
        type.title_banner = title_banner
        type.image_banner = image_banner

    # 获取登录用户购物车中商品的数量
    cart_count = 0

    # 组织上下文
    context = {'types': types,
               'index_banner': index_banner,
               'promotion_banner': promotion_banner,
               'cart_count': cart_count}

    # 生成静态首页内容 render->HttpResponse对象
    # 1.加载模板文件
    temp = loader.get_template('static_index.html')
    # 2.模板渲染:产生html的内容
    static_html = temp.render(context)

    # 保存静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_html)

















