from django.conf.urls import patterns, url


urlpatterns = patterns('student.views',
    url(r'^dashboard/$', 'dashboard', name='student_dashboard'),
    url(r'^test/(?P<pk>\d+)/$', 'pass_test', name='student_pass_test'),
    url(r'^test/(?P<pk>\d+)/start/$', 'start_test', name='student_start_test'),
)
