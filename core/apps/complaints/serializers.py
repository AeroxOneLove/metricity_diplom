from __future__ import annotations

from rest_framework import serializers

from core.apps.complaints.models import Complaint, ComplaintStatus, IncomingReport
from core.apps.complaints.services import make_cell_id
from core.apps.moderation.models import Decision


class IncomingReportCreateSerializer(serializers.ModelSerializer):
    declared_category = serializers.ChoiceField(choices=IncomingReport._meta.get_field("declared_category").choices)
    text = serializers.CharField(required=False, allow_blank=True)
    photo = serializers.ImageField(required=False, allow_null=True)
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lon = serializers.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        model = IncomingReport
        fields = ("declared_category", "text", "photo", "lat", "lon")
        extra_kwargs = {field_name: {"write_only": True} for field_name in fields}

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        text = str(attrs.get("text") or "").strip()
        photo = attrs.get("photo")
        if not text and not photo:
            raise serializers.ValidationError("Нужно передать текст жалобы, фотографию или оба поля сразу.")
        return attrs

    def create(self, validated_data: dict[str, object]) -> IncomingReport:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            raise serializers.ValidationError("Не удалось определить автора жалобы.")

        lat = validated_data["lat"]
        lon = validated_data["lon"]
        return IncomingReport.objects.create(
            user=user,
            cell_id=make_cell_id(lat=lat, lon=lon),
            **validated_data,
        )


class ComplaintMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ("id", "lat", "lon", "category", "status", "priority_score")
        read_only_fields = fields


class ComplaintDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = (
            "id",
            "category",
            "status",
            "lat",
            "lon",
            "cell_id",
            "stack_count",
            "priority_score",
            "ai_verified",
            "ai_confidence",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReportCreateResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)


class ComplaintConfirmSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True)
    photo = serializers.ImageField(required=False, allow_null=True)


class ComplaintStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ComplaintStatus.choices)


class ComplaintStatusUpdateResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)


class IncomingQueueSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = IncomingReport
        fields = (
            "id",
            "user_id",
            "declared_category",
            "text",
            "photo",
            "lat",
            "lon",
            "cell_id",
            "status",
            "ai_pred_category",
            "ai_confidence",
            "created_at",
        )
        read_only_fields = fields


class ModerationDecisionRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=Decision.choices)
    note = serializers.CharField(required=False, allow_blank=True)


class ModerationDecisionResponseSerializer(serializers.Serializer):
    incoming_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    complaint = ComplaintDetailSerializer(read_only=True, allow_null=True)
