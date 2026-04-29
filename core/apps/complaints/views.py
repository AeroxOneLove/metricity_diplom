from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.accounts.permissions import CanSetPriority, IsModerator
from core.apps.complaints.models import Complaint, IncomingReport, IncomingStatus
from core.apps.complaints.serializers import (
    ComplaintConfirmSerializer,
    ComplaintDetailSerializer,
    ComplaintMapSerializer,
    ComplaintStatusUpdateResponseSerializer,
    ComplaintStatusUpdateSerializer,
    IncomingQueueSerializer,
    IncomingReportCreateSerializer,
    ModerationDecisionRequestSerializer,
    ModerationDecisionResponseSerializer,
    ReportCreateResponseSerializer,
)
from core.apps.complaints.services import attach_to_master, confirm_complaint
from core.apps.complaints.services.querying import filter_complaints
from core.apps.complaints.services.statuses import change_complaint_status
from core.apps.complaints.tasks import run_ai_check
from core.apps.moderation.models import Decision, ModerationDecision


class ReportCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IncomingReportCreateSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incoming = serializer.save()
        run_ai_check.delay(incoming.id)

        response_serializer = ReportCreateResponseSerializer(
            {
                "id": incoming.id,
                "status": incoming.status,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ComplaintListPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class ComplaintListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ComplaintMapSerializer
    pagination_class = ComplaintListPagination
    queryset = Complaint.objects.all()

    def get_queryset(self):
        return filter_complaints(
            super().get_queryset(),
            self.request.query_params,
        )


class ComplaintDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ComplaintDetailSerializer
    queryset = Complaint.objects.all()


class ComplaintStatusUpdateView(APIView):
    permission_classes = [IsModerator]

    def post(self, request: Request, pk: int) -> Response:
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_complaint = change_complaint_status(
                complaint=complaint,
                new_status=serializer.validated_data["status"],
                moderator=request.user,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

        response_serializer = ComplaintStatusUpdateResponseSerializer(
            {
                "id": updated_complaint.id,
                "status": updated_complaint.status,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ConfirmView(APIView):
    permission_classes = [CanSetPriority]

    def post(self, request: Request, pk: int) -> Response:
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_complaint, created = confirm_complaint(
                complaint=complaint,
                user_id=request.user.id,
                text=serializer.validated_data.get("text", ""),
                photo=serializer.validated_data.get("photo"),
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(ComplaintDetailSerializer(updated_complaint).data, status=response_status)


class IncomingQueueView(generics.ListAPIView):
    permission_classes = [IsModerator]
    serializer_class = IncomingQueueSerializer

    def get_queryset(self):
        return (
            IncomingReport.objects.select_related("user")
            .filter(status=IncomingStatus.NEEDS_MODERATION)
            .order_by("created_at")
        )


class DecisionView(APIView):
    permission_classes = [IsModerator]

    def post(self, request: Request, pk: int) -> Response:
        incoming = get_object_or_404(IncomingReport.objects.select_related("user"), pk=pk)

        if incoming.status != IncomingStatus.NEEDS_MODERATION:
            raise serializers.ValidationError({"detail": "Этот отчёт не находится в очереди модерации."})

        if ModerationDecision.objects.filter(incoming=incoming).exists():
            raise serializers.ValidationError({"detail": "По этому отчёту решение уже принято."})

        serializer = ModerationDecisionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]
        note = serializer.validated_data.get("note", "")

        complaint: Complaint | None = None

        with transaction.atomic():
            ModerationDecision.objects.create(
                incoming=incoming,
                moderator=request.user,
                decision=decision,
                note=note,
            )

            if decision == Decision.APPROVE:
                incoming.status = IncomingStatus.PROCESSED
                complaint = attach_to_master(incoming)
            else:
                incoming.status = IncomingStatus.REJECTED

            incoming.save(update_fields=["cell_id", "status", "updated_at"])

        response_serializer = ModerationDecisionResponseSerializer(
            {
                "incoming_id": incoming.id,
                "status": incoming.status,
                "complaint": complaint,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
