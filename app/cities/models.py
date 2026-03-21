from django.conf import settings
from django.db import models


class FavoriteCity(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_cities",
    )
    city_slug = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "city_slug"],
                name="cities_favorite_user_city_slug_unique",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} → {self.city_slug}"
