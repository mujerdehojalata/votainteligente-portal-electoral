from django.conf.urls import url
from backend_citizen.views import (MyProposalsView,
                                   PopularProposalTemporaryDataUpdateView,
                                   UpdateUserView,
                                   OrganizationDetailView,
                                   OrganizationCreateView,
                                   DoYouBelongToAnOrgView,
                                   GroupRegistrationView,
                                   MySupportsView,
                                   MyStats,
                                   )
from django.contrib.auth.views import password_reset


urlpatterns = [
                       url(r'^$',
                           MyProposalsView.as_view(),
                           name='my_proposals'),
                       url(r'^create_group/?$',
                           GroupRegistrationView.as_view(),
                           name='create_group'),
                       url(r'^organization/(?P<slug>[-\w]+)/?$',
                           OrganizationDetailView.as_view(),
                           name='organization'),
                       url(r'^update/?$',
                           UpdateUserView.as_view(),
                           name='update_my_profile'),
                       url(r'^my_supports/?$',
                           MySupportsView.as_view(),
                           name='my_supports'),
                       url(r'^stats/?$',
                           MyStats.as_view(),
                           name='stats'),
                       url(r'^create_organization/?$',
                           OrganizationCreateView.as_view(),
                           name='create_org'),
                       url(r'^do_you_belong_to_an_org/?$',
                           DoYouBelongToAnOrgView.as_view(),
                           name='do_you_belong_to_an_org'),
                       url(r'^update_temporary_data/(?P<pk>[\d]+)/?$',
                           PopularProposalTemporaryDataUpdateView.as_view(),
                           name='temporary_data_update'),
]
