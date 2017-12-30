from django.shortcuts import render, redirect
from django.views.generic import View
from django.core.urlresolvers import reverse
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo,OrderGoods
from django.http import JsonResponse
from apps.user.models import Address
from datetime import datetime
from django.db import transaction
from alipay import AliPay
from django.conf import settings
import os

# Create your views here.

class OrderPlaceView(View):

    def post(self,request):


        sku_ids = request.POST.getlist('sku_ids')
        print(sku_ids)
        if not all(sku_ids):
            return redirect(reverse('cart:show'))

        user = request.user

        if  not user.is_authenticated():
            return redirect(reverse('goods:index'))

        # 获取sku,count,给sku赋值
        conn = get_redis_connection('default')
        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            cart_key = "cart_%d"%user.id
            count = conn.hget(cart_key,sku_id)
            amount = int(count)*sku.price
            sku.amount = amount
            sku.count = count
            total_count += int(count)
            total_price += amount
            skus.append(sku)

        transit_price = 10
        total_pay = total_price + transit_price
        addrs = Address.objects.filter(user=user)
        sku_ids = ','.join(sku_ids)
        context = {'addrs':addrs,
                   'total_count':total_count,
                   'total_price':total_price,
                   'total_pay':total_pay,
                   'transit_price':transit_price,
                   'skus':skus,
                   'sku_ids':sku_ids
                   }

        return render(request,'place_order.html',context)

# 悲观锁
class OrderCommitView1(View):

    @transaction.atomic
    def post(self,request):

        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        if not all([addr_id,pay_method,sku_ids]):
            return  JsonResponse({'res':1,'errmsg':'数据不完整'})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'地址信息错误'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':3,'errmsg':'支付方式无效'})

        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        transit_price = 10
        total_count = 0
        total_price = 0

        sid = transaction.savepoint()

        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)
            conn = get_redis_connection('default')
            cart_key = "cart_%d"%user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:

                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res':0,'errmsg':'商品不存在'})

                count = conn.hget(cart_key,sku_id)
                OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=sku.price
                )
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                total_count += int(count)
                total_price += sku.price*int(count)

            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return JsonResponse({'res':7,'errmsg':'下单失败'})

        transaction.savepoint_commit(sid)

        conn.hdel(cart_key,*sku_ids)
        return JsonResponse({'res':5, 'message':'订单创建成功！'})

# 乐观锁
class OrderCommitView(View):

    @transaction.atomic
    def post(self,request):

        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        if not all([addr_id,pay_method,sku_ids]):
            return  JsonResponse({'res':1,'errmsg':'数据不完整'})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'地址信息错误'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':3,'errmsg':'支付方式无效'})

        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        transit_price = 10
        total_count = 0
        total_price = 0

        sid = transaction.savepoint()

        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)
            conn = get_redis_connection('default')
            cart_key = "cart_%d"%user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({'res':0,'errmsg':'商品不存在'})

                    count = conn.hget(cart_key,sku_id)

                    if int(count)>sku.stock:
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({'res':6, 'errmsg':'商品库存不足'})
                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales =sku.sales + int(count)

                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(sid)
                            return JsonResponse({'res':7,'errmsg':'下单失败！'})
                        continue
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )
                    # sku.stock -= int(count)
                    # sku.sales += int(count)
                    # sku.save()

                    total_count += int(count)
                    total_price += sku.price*int(count)

                    break

            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return JsonResponse({'res':7,'errmsg':'下单失败'})

        transaction.savepoint_commit(sid)

        conn.hdel(cart_key,*sku_ids)
        return JsonResponse({'res':5, 'message':'订单创建成功！'})

class OrderPayView(View):

    def post(self,request):

        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        order_id = request.POST.get('order_id')

        if not order_id:
            return JsonResponse({'res':1, 'errmsg':'订单id错误'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2,'errmsg':'订单信息错误'})

        alipay = AliPay(
            appid="2016090800462728",
            app_notify_url=None,
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),  # 网站私钥文件的路径
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            sign_type="RSA2",
            debug= True
        )

        total_amount = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            subject='天天生鲜%s'%order_id,
            out_trade_no=order_id,
            total_amount=str(total_amount),
            return_url=None,
            notify_url=None
        )
        pay_url = "https://openapi.alipaydev.com/gateway.do?" + order_string

        return JsonResponse({'res':3, 'pay_url':pay_url})

class OrderCheckView(View):

    def post(self, request):
        '''获取支付结果'''
        # 登录判断
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 参数校验
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '订单id错误'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单信息错误'})

        # 业务处理：调用支付宝下单支付接口 sdk
        # 初始化
        alipay = AliPay(
            appid="2016090800462728",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),  # 网站私钥文件的路径
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        while True:
            response = alipay.api_alipay_trade_query(out_trade_no=order_id)
            code = response.get('code')
            print('code:%s'%code)

            if code == '10000' and response.get('trade_status') == "TRADE_SUCCESS":

                trade_no = response.get('trade_no')
                order.order_status = 4
                order.trade_no = trade_no
                order.save()
                return JsonResponse({'res':4, 'message':'支付成功'})

            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):

                import time
                time.sleep(5)
                continue

            else:
                return JsonResponse({'res':3, 'errmsg':'支付出错'})


class CommentView(View):

    def get(self,request, order_id):

        user = request.user

        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount = order_sku.count*order_sku.price
            order_sku.amount = amount

        order.order_skus = order_skus

        return render(request, "order_comment.html",{"order": order})

    def post(self, request, order_id):

        user = request.user

        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        for i in range(1,total_count + 1):

            sku_id = request.POST.get("sku_%d"%i)
            content = request.POST.get('content_%d'%i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5
        order.save()

        return redirect(reverse("user:order", kwargs={"page": 1}))























