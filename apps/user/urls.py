from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from apps.user.views import RegisterView,LoginView,ActiveView,LogoutView,UserInfoView,UserOrderView,AddressView

urlpatterns = [
    url(r'^register$',RegisterView.as_view(),name='register'),
    url(r'^active/(?P<token>.*)$',ActiveView.as_view(),name='active'),
    url(r'^login$',LoginView.as_view(),name='login'),
    url(r'^logout',LogoutView.as_view(),name='logout'),
    url(r'^userinfo',login_required(UserInfoView.as_view()),name='userinfo'),
    url(r'^order/(?P<page>\d+)$', login_required(UserOrderView.as_view()), name='order'), # 用户中心-订单页
    url(r'address',login_required(AddressView.as_view()),name='address')
]