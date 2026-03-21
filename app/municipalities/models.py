from django.conf import settings
from django.db import models


class FavoriteMunicipality(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_municipalities",
    )
    municipality_slug = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "municipality_slug"],
                name="municipalities_favorite_user_municipality_slug_unique",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} → {self.municipality_slug}"
