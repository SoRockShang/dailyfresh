from django.contrib import admin
from django.core.cache import cache
from apps.goods.models import GoodsType,IndexTypeGoodsBanner,IndexPromotionBanner,IndexGoodsBanner,Goods,GoodsImage,GoodsSKU

# Register your models here.

class BaseAdmin(admin.ModelAdmin):
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)

        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        cache.delete('index_page_data')

    def delte_model(self,request,obj):

        super().delete_model(request,obj)

        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()
        cache.delete('index_page_data')



class GoodsTypeAdmin(BaseAdmin):
    pass


class IndexGoodsBannerAdmin(BaseAdmin):
    pass


class IndexPromotionBannerAdmin(BaseAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseAdmin):
    pass


admin.site.register(GoodsType)
admin.site.register(IndexGoodsBanner)
admin.site.register(IndexPromotionBanner)