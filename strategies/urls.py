from django.conf.urls import patterns, url
from strategies import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^about/', views.about, name='about'),
	url(r'^display_hichart/$', views.display_hichart, name='display_hichart'),
	)