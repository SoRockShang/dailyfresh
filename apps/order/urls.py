from django.conf.urls import url
from apps.order.views import OrderPlaceView,OrderCommitView,OrderPayView,OrderCheckView,CommentView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url(r'^place$', login_required(OrderPlaceView.as_view()), name='place'), # 提交订单页面显示
    url(r'^commit$',login_required(OrderCommitView.as_view()),name='commit'),
    url(r'^pay$',OrderPayView.as_view(),name='pay'),
    url(r'^check$',OrderCheckView.as_view(),name='check'),
    url(r'^comment/(?P<order_id>.+)$', CommentView.as_view(), name='comment')  # 订单评论
]