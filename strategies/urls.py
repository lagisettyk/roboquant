from django.conf.urls import patterns, url
from strategies import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^about/', views.about, name='about'),
	url(r'^display_hichart/$', views.display_hichart, name='display_hichart'),
	url(r'^charts/$', views.display_matplotlib, name='display_matplotlib'),
	url(r'^simulate/$', views.display_backtest, name='display_backtest'),
	url(r'^portfolio/$', views.display_portfolio, name='display_portfolio'),
	url(r'^indicators/$', views.display_indicators, name='display_indicators'),
	url(r'^backtest_results/$', views.backtest, name='backtest'),
	url(r'^backtest_portfolio/$', views.backtestPortfolio, name='backtestPortfolio'),
	url(r'^backtest_indicators/$', views.computeIndicators, name='computeIndicators'),
	url(r'^hichart_quandl/$', views.hichart_quandl, name='hichart_quandl'),
	url(r'^hichart_redis/$', views.hichart_redis, name='hichart_redis'),
	url(r'^charts/simple.png$', views.simple, name='simple'),
	)