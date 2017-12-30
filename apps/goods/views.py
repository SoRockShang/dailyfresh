from django.shortcuts import render,redirect
from django.views.generic import View
from apps.goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner,GoodsSKU
from apps.order.models import OrderGoods
from django_redis import get_redis_connection
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator


# Create your views here.

class IndexView(View):

    def get(self,request):

        context = cache.get('index_page_data')
        if context is None:
            print('设置缓存')
            # 商品分类
            types = GoodsType.objects.all()
            #首页轮播
            index_banner = IndexGoodsBanner.objects.all().order_by('index')
            # 促销
            promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
            # 获取首页分类商品 展示信息
            for type in types:
                title_banner = IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by('index')
                image_banner = IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')
                type.title_banner = title_banner
                type.image_banner = image_banner

            user = request.user

            cart_count = 0

            if user.is_authenticated():
                conn = get_redis_connection('default')
                cart_key = 'cart_%d'%user.id
                cart_count = conn.hlen(cart_key)

            context = {'types':types,
                       'index_banner':index_banner,
                       'promotion_banner':promotion_banner,
                       'cart_count':cart_count}
            cache.set('index_page_data',context,3600)

        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)
        context.update(cart_count=cart_count)

        return render(request,'index.html',context)

class DetailView(View):

    def get(self,request,sku_id):

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-creat_time')[:2]
        order_skus = OrderGoods.objects.filter(sku=sku).order_by('-update_time')
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku_id)

        user = request.user

        cart_count = 0
        # 商品分类
        types = GoodsType.objects.all()
        if user.is_authenticated():
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车商品条目数
            cart_count = conn.hlen(cart_key)

            conn = get_redis_connection('default')
            history_key = 'history_%d'%user.id
            conn.lrem(history_key,0,sku_id)
            conn.lpush(history_key,sku_id)

            conn.ltrim(history_key,0,4)

        context = {'sku':sku,
                   'new_skus':new_skus,
                   'order_skus':order_skus,
                   'same_spu_skus':same_spu_skus,
                   'types':types,
                   'cart_count':cart_count}

        # 使用模板
        return render(request, 'detail.html', context)

class ListView(View):

    def get(self,request,type_id,page):

        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))

        sort = request.GET.get('sort','default')
        # 商品分类
        types = GoodsType.objects.all()
        if sort == 'price':
            skus  =GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        paginator = Paginator(skus,2)
        page = int(page)

        if page > paginator.num_pages or page <= 0:
            page = 1

        skus_page = paginator.page(page)

        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3:
            pages = range(1,6)
        elif num_pages -page <=2:
            pages = range(num_pages-4,num_pages+1)
        else:
            pages = range(page-2,page+3)

        new_skus = GoodsSKU.objects.filter(type=type).order_by('-creat_time')[:2]

        user = request.user
        # 获取用户购物车中商品的条目数
        cart_count = 0
        if user.is_authenticated():
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车商品条目数
            cart_count = conn.hlen(cart_key)

        # 组织上下文
        context = {'type':type,
                   'skus_page':skus_page,
                   'new_skus':new_skus,
                   'cart_count':cart_count,
                   'types':types,
                   'sort':sort}

        # 使用模板
        return render(request, 'list.html', context)

