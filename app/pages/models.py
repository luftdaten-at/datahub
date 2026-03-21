from django.conf import settings
from django.db import models


class FAQEntry(models.Model):
    """FAQ items for the public help page; staff edit via Django admin."""

    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers appear first.",
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faq_entries_updated",
    )

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "FAQ entry"
        verbose_name_plural = "FAQ entries"

    def __str__(self):
        return self.question
