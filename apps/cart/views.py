from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection


# Create your views here.
class CartAddView(View):

    def post(self, request):


        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:

            return JsonResponse({'res':2, 'errmsg':'数据不存在'})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':3, 'errmsg':'商品数目不合法'})

        if count<= 0:
            return JsonResponse({'res':3, 'errmsg':'商品数目不合法'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        cart_count = conn.hget(cart_key,sku_id)
        print(111111)

        if cart_count:
            count += int(cart_count)

        if count >sku.stock:
            return JsonResponse({'res':4, 'errmsg':'商品库存不足'})

        conn.hset(cart_key, sku_id, count)

        cart_count = conn.hlen(cart_key)

        return JsonResponse({'res':5, 'cart_count':cart_count, 'message':'添加成功！'})

class CartInfoView(View):

    def get(self,request):

        user = request.user

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        cart_dict = conn.hgetall(cart_key)

        skus = []
        total_count = 0
        total_price = 0
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)

            amount = sku.price*int(count)

            sku.count = count
            sku.amount = amount

            skus.append(sku)

            total_count += int(count)
            total_price +=amount

        context = {'total_count':total_count,
                   'total_price':total_price,
                   'skus':skus}

        return render(request, 'cart.html',context)


class CartUpdateView(View):

    def post(self,request):

        user = request.user

        if not user.is_authenticated():
            return JsonResponse({"res":0, "errmsg":'用户未登录！'})

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id,count]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整！'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({"res":2, "errmsg":"商品不存在"})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':3, 'errmsg':'数量为数字！'})

        if count<0:
            return JsonResponse({'res':3, 'errmsg':'数量不合法'})



        conn = get_redis_connection('default')
        cart_key = "cart_%d"%user.id
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足！'})
        conn.hset(cart_key,sku_id,count)
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:

            total_count += int(val)

        return JsonResponse({'res':5, 'total_count':total_count, 'message':'更新成功'})


class CartDeleteView(View):
    '''购物车记录的删除'''
    def post(self, request):
        # 获取user
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        sku_id = request.POST.get('sku_id')

        # 参数校验
        if not sku_id:
            # 数据不完整
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验商品id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理: 购物车记录删除
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # 删除redis中sku_id
        conn.hdel(cart_key, sku_id)

        # 计算用户购物车中商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        # 返回应答
        return JsonResponse({'res':3, 'total_count':total_count, 'message':'删除成功'})
























