from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.apps.accounts.models import UserRatingReason
from core.apps.accounts.permissions import CanSetPriority, IsModerator
from core.apps.accounts.services import change_user_rating
from core.apps.complaints.models import (
    Complaint,
    ComplaintImportanceVote,
    IMPORTANCE_WEIGHTS,
    IncomingReport,
    IncomingStatus,
)
from core.apps.complaints.serializers import (
    ComplaintConfirmSerializer,
    ComplaintDetailSerializer,
    ComplaintImportanceRequestSerializer,
    ComplaintImportanceResponseSerializer,
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
from core.apps.complaints.services.priority import recalculate_priority_score
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

        if created:
            change_user_rating(
                request.user,
                1,
                UserRatingReason.CONFIRMED_COMPLAINT,
                complaint=updated_complaint,
            )

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(ComplaintDetailSerializer(updated_complaint).data, status=response_status)


class ComplaintImportanceView(APIView):
    permission_classes = [CanSetPriority]

    def post(self, request: Request, pk: int) -> Response:
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintImportanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        importance = serializer.validated_data["importance"]
        weight = IMPORTANCE_WEIGHTS[importance]

        with transaction.atomic():
            ComplaintImportanceVote.objects.update_or_create(
                complaint=complaint,
                user=request.user,
                defaults={
                    "importance": importance,
                    "weight": weight,
                },
            )
            updated_complaint = recalculate_priority_score(complaint)

        response_serializer = ComplaintImportanceResponseSerializer(
            {
                "complaint_id": updated_complaint.id,
                "importance": importance,
                "priority_score": updated_complaint.priority_score,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


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
        reason = serializer.validated_data.get("reason", serializer.validated_data.get("note", ""))
        final_category = serializer.validated_data.get("category")

        complaint: Complaint | None = None

        with transaction.atomic():
            if decision == Decision.APPROVE:
                final_category = final_category or incoming.declared_category

            ModerationDecision.objects.create(
                incoming=incoming,
                moderator=request.user,
                decision=decision,
                note=reason,
                reason=reason,
                final_category=final_category if decision == Decision.APPROVE else None,
            )

            if decision == Decision.APPROVE:
                incoming.status = IncomingStatus.PROCESSED
                complaint = attach_to_master(incoming, category=final_category)
                change_user_rating(
                    incoming.user,
                    5,
                    UserRatingReason.MODERATOR_APPROVED_REPORT,
                    incoming_report=incoming,
                )
            else:
                incoming.status = IncomingStatus.REJECTED
                change_user_rating(
                    incoming.user,
                    -3,
                    UserRatingReason.MODERATOR_REJECTED_REPORT,
                    incoming_report=incoming,
                )

            incoming.save(update_fields=["cell_id", "status", "updated_at"])

        response_serializer = ModerationDecisionResponseSerializer(
            {
                "incoming_id": incoming.id,
                "status": incoming.status,
                "complaint": complaint,
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
