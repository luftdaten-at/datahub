"""Views for workshop spots API (create, delete, list)."""
from django.http import JsonResponse
from django.contrib.gis.geos import Point
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from main.util import get_avg_temp_per_spot
from workshops.models import Workshop, WorkshopSpot

from api.serializers import WorkshopSpotSerializer, WorkshopSpotPkSerializer


@extend_schema(
    tags=["workshops"],
    summary="Create a workshop spot",
    description="Creates a new hot or cool spot (circle) on a workshop map. Requires authentication and workshop owner permissions.",
    request=WorkshopSpotSerializer,
    responses={
        201: {"description": "Spot created successfully"},
        400: {"description": "Invalid request data"},
        403: {"description": "Permission denied - user is not the workshop owner"},
        404: {"description": "Workshop not found"},
    },
    examples=[
        OpenApiExample(
            "Create hot spot",
            value={"workshop": "homrh8", "lat": 48.2112, "lon": 16.3736, "radius": 100.0, "type": "hot"},
            request_only=True,
        ),
        OpenApiExample(
            "Create cool spot",
            value={"workshop": "homrh8", "lat": 48.2200, "lon": 16.3800, "radius": 150.0, "type": "cool"},
            request_only=True,
        ),
    ],
)
class CreateWorkshopSpotAPIView(APIView):
    serializer_class = WorkshopSpotSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        j = request.data
        workshop = Workshop.objects.filter(pk=j["workshop"]).first()
        if workshop is None:
            raise ValidationError("Workshop doesn't exists")
        if not (request.user.is_superuser or request.user == workshop.owner):
            raise PermissionDenied("You don't have the permissions to add a spot to this workshop")

        center = Point(j["lon"], j["lat"], srid=4326)
        center.transform(3857)
        circle_polygon = center.buffer(j["radius"], quadsegs=32)
        circle_polygon.transform(4326)

        WorkshopSpot.objects.get_or_create(
            workshop=workshop,
            center=center,
            radius=j["radius"],
            area=circle_polygon,
            type=j["type"],
        )

        return Response(status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["workshops"],
    summary="Delete a workshop spot",
    description="Deletes an existing workshop spot. Requires authentication and workshop owner permissions.",
    request=WorkshopSpotPkSerializer,
    responses={
        200: {"description": "Spot deleted successfully"},
        400: {"description": "Invalid request data"},
        403: {"description": "Permission denied - user is not the workshop owner"},
        404: {"description": "Workshop or workshop spot not found"},
    },
    examples=[
        OpenApiExample("Delete spot", value={"workshop": "homrh8", "workshop_spot": 123}, request_only=True),
    ],
)
class DeleteWorkshopSpotAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = WorkshopSpotPkSerializer

    def post(self, request, *args, **kwargs):
        j = request.data
        workshop = Workshop.objects.filter(pk=j["workshop"]).first()
        if workshop is None:
            raise ValidationError("Workshop doesn't exists")
        if not (request.user.is_superuser or request.user == workshop.owner):
            raise PermissionDenied("You don't have the permissions to add a spot to this workshop")

        workshop_spot = WorkshopSpot.objects.filter(pk=j["workshop_spot"]).first()
        if workshop_spot is None:
            raise ValidationError("Workshop spot doesn't exists")

        workshop_spot.delete()
        return Response(status=status.HTTP_200_OK)


@extend_schema(
    tags=["workshops"],
    summary="Get workshop spots",
    description="Retrieves all spots (hot and cool areas) for a specific workshop, including their average temperatures.",
    parameters=[
        OpenApiParameter(
            name="pk",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Workshop name (primary key)",
            required=True,
            examples=[OpenApiExample("Example workshop", value="homrh8")],
        )
    ],
    responses={
        200: {"description": "List of workshop spots with coordinates, radius, type, and average temperature"},
        400: {"description": "Invalid workshop name"},
        404: {"description": "Workshop not found"},
    },
)
class GetWorkshopSpotsAPIView(APIView):
    serializer_class = WorkshopSpotPkSerializer

    def get(self, request, pk, *args, **kwargs):
        workshop = Workshop.objects.filter(pk=pk).first()
        if workshop is None:
            raise ValidationError("Workshop doesn't exists")

        mean_temperature = {ws_id: mean_temp for ws_id, mean_temp in get_avg_temp_per_spot(pk)}
        ret = []
        for workshop_spot in workshop.workshop_spots.all():
            ret.append({
                "pk": workshop_spot.pk,
                "lon": workshop_spot.center.x,
                "lat": workshop_spot.center.y,
                "radius": workshop_spot.radius,
                "type": workshop_spot.type,
                "temperature": mean_temperature.get(workshop_spot.id, None),
            })

        return JsonResponse(ret, status=200, safe=False)
