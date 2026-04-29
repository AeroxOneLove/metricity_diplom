from django.urls import path

from core.apps.complaints.views import (
    ComplaintDetailView,
    ComplaintListView,
    ComplaintStatusUpdateView,
    ConfirmView,
    DecisionView,
    IncomingQueueView,
    ReportCreateView,
)


app_name = "complaints"


urlpatterns = [
    path("reports/", ReportCreateView.as_view(), name="report-create"),
    path("complaints/", ComplaintListView.as_view(), name="complaint-list"),
    path("complaints/<int:pk>/", ComplaintDetailView.as_view(), name="complaint-detail"),
    path("complaints/<int:pk>/status/", ComplaintStatusUpdateView.as_view(), name="complaint-status"),
    path("complaints/<int:pk>/confirm/", ConfirmView.as_view(), name="complaint-confirm"),
    path("moderation/incoming/", IncomingQueueView.as_view(), name="incoming-queue"),
    path("moderation/incoming/<int:pk>/decision/", DecisionView.as_view(), name="incoming-decision"),
]
