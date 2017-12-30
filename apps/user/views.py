from django.shortcuts import render,redirect
from django.views.generic import View
from apps.user.models import User,Address
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
# from apps.user.send import send_register_active_email
from django.contrib.auth import authenticate,login,logout
from celery_tasks.tasks import send_register_active_email
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo, OrderGoods
from django.core.paginator import Paginator

import re

# Create your views here.

class RegisterView(View):

    def get(self,request):
        return render(request,'register.html')

    def post(self,request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        if not all([username,password,email]):
            return render(request,'register.html',{'errmsg':'请完成页面内容再提交'})

        if allow !='on':
            return render(request,'register.html',{'errmsg':'请同意协议'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            return render(request,'register.html',{'errmsg':'请输入正确的邮箱格式'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request,'register.html',{'errmsg':'用户以存在'})

        user = User.objects.create_user(username,email,password)
        user.is_active = 0
        user.save()

        serializer = Serializer(settings.SECRET_KEY,3600)
        info = {'confirm':user.id}
        token = serializer.dumps(info)
        token = token.decode()

        send_register_active_email.delay(email,username,token)

        return redirect(reverse('goods:index'))

class ActiveView(View):

    def get(self,request,token):

        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired:
            return HttpResponse('链接已过期 ')

class LoginView(View):

    def get(self,request):
        if 'username' in request.COOKIES:
            username = request.COOKIES['username']
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request,'login.html',{'username':username,'checked':checked})


    def post(self,request):

        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')

        if not all([username,password]):
            return render(request,'login.html',{'errmsg':'上方不能为空！'})

        user = authenticate(username=username,password=password)
        if user is not None:
            if user.is_active:
                login(request,user)
                response = redirect(reverse('goods:index'))

                if remember == 'on':
                    response.set_cookie('username',username,max_age=30)
                else:
                    response.delete_cookie('username')
                return response
            else:
                return render(request,'login.html',{'errmsg':'用户未激活'})
        else:
            return render(request,'login.html',{'errmsg':'用户名或密码错误'})

class LogoutView(View):
    def get(self,request):
        logout(request)
        return redirect(reverse('goods:index'))


class UserInfoView(View):
    def get(self,request):
        # 获取登陆用户
        user = request.user
        # 获取用户默认地址
        address = Address.objects.get_default_address(user)
        # 获取浏览记录
        conn = get_redis_connection('default')
        history_key = "history_%d"%user.id
        # 获取最近5条
        sku_ids = conn.lrange(history_key,0,4)
        skus = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id = sku_id)
            skus.append(sku)
        context = {
            'address':address,
            'skus':skus,
            'page':'user'
        }

        # 拼接上下文
        return render(request,'user_center_info.html',context)

class UserOrderView(View):
    def get(self,request, page):
        user =request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-creat_time')

        for order in orders:
            order_skus = OrderGoods.objects.filter(order=order)
            for order_sku in order_skus:
                amount = order_sku.count*order_sku.price
                order_sku.amount = amount
            total_amount = order.total_price + order.transit_price
            status_name = OrderInfo.ORDER_STATUS[order.order_status]
            order.order_skus = order_skus
            order.total_amount = total_amount
            order.status_name = status_name

        paginator = Paginator(orders,2)

        page = int(page)

        if page > paginator.num_pages or page <= 0:
            page = 1

        order_page = paginator.page(page)

        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {'order_page': order_page,
                   'pages': pages,
                   'page': 'order'}

        # 使用模板
        return render(request, 'user_center_order.html', context)


class AddressView(View):
    def get(self,request):

        user = request.user
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'address': address, 'page': 'addr'})

    def post(self,request):

        #接受参数
        # user = request.user
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 参数校验

        if not all([receiver,addr,phone]):

            return render(request,'user_center_site.html',{'errmsg':'信息不完整！'})

        #添加地址

        user = request.user
        address = Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True

        Address.objects.create(
            user = user,
            receiver = receiver,
            addr  = addr,
            zip_code = zip_code,
            phone = phone,
            is_default = is_default
        )

        return redirect(reverse('user:address'))






