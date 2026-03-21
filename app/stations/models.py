from django.conf import settings
from django.db import models


class FavoriteStation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_stations",
    )
    station_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "station_id"],
                name="stations_favorite_user_station_unique",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} → {self.station_id}"
