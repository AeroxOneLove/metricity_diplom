from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.apps.accounts.models import UserLevel, UserRatingEvent, UserRatingReason
from core.apps.accounts.services import change_user_rating
from core.apps.complaints.models import Category, Complaint, ComplaintStatus


User = get_user_model()


class ChangeUserRatingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")
        self.complaint = Complaint.objects.create(
            category=Category.TRASH,
            status=ComplaintStatus.PUBLISHED,
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            stack_count=0,
            priority_score=0,
        )

    def test_rating_increases(self):
        change_user_rating(self.user, 5, UserRatingReason.OTHER)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 5)

    def test_rating_decreases(self):
        self.user.profile.rating = 10
        self.user.profile.save()

        change_user_rating(self.user, -3, UserRatingReason.MODERATOR_REJECTED_REPORT)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 7)

    def test_event_created(self):
        event = change_user_rating(
            self.user,
            5,
            UserRatingReason.CONFIRMED_COMPLAINT,
            complaint=self.complaint,
        )

        self.assertEqual(UserRatingEvent.objects.count(), 1)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.delta, 5)
        self.assertEqual(event.reason, UserRatingReason.CONFIRMED_COMPLAINT)
        self.assertEqual(event.complaint, self.complaint)

    def test_duplicate_event_not_created(self):
        first_event = change_user_rating(
            self.user,
            5,
            UserRatingReason.CONFIRMED_COMPLAINT,
            complaint=self.complaint,
        )
        second_event = change_user_rating(
            self.user,
            5,
            UserRatingReason.CONFIRMED_COMPLAINT,
            complaint=self.complaint,
        )

        self.assertEqual(first_event, second_event)
        self.assertEqual(UserRatingEvent.objects.count(), 1)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 5)

    def test_newbie_becomes_active_after_10(self):
        change_user_rating(self.user, 10, UserRatingReason.OTHER)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 10)
        self.assertEqual(self.user.profile.level, UserLevel.ACTIVE)

    def test_active_becomes_trusted_after_50(self):
        change_user_rating(self.user, 50, UserRatingReason.OTHER)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 50)
        self.assertEqual(self.user.profile.level, UserLevel.TRUSTED)

    def test_moderator_level_is_not_changed_automatically(self):
        self.user.profile.level = UserLevel.MODERATOR
        self.user.profile.is_level_manual = True
        self.user.profile.save()

        change_user_rating(self.user, -100, UserRatingReason.OTHER)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, -100)
        self.assertEqual(self.user.profile.level, UserLevel.MODERATOR)
