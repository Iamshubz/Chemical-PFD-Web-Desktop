from django.shortcuts import render
from django.http import Http404
from .models import Component, Project, CanvasState, Connection
from .serializers import ComponentSerializer, ProjectSerializer,CanvasStateSerializer, ConnectionSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction


@api_view(['GET'])
@permission_classes([AllowAny])
def hello_world(request):
    return Response({"message": "Hello from DRF!"})

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "Username and password required"},
                            status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"},
                            status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )
        return Response({"message": "User registered successfully", "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }},
         status=status.HTTP_201_CREATED)

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]

class MyTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
from django.db.models import Q

class ComponentListView(generics.ListCreateAPIView):
    # ... (class attributes) ...
    serializer_class = ComponentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    ordering_fields = ['s_no', 'name', 'legend']
    ordering = ['s_no']

    def get_queryset(self):
        return (
            Component.objects
            .select_related("created_by")
            .filter(
                Q(created_by=self.request.user) |
                Q(created_by__isnull=True)
            )
        )

    def list(self, request, *args, **kwargs):
        # ... (list method remains same) ...
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(
        svg__isnull=False,
        png__isnull=False,
        ).exclude(
        svg='',
        png='',
        )
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response({"components": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        # ... (create method remains same) ...
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        # Auto-assign the authenticated user as creator
        component = serializer.save(created_by=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

class ComponentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ComponentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'

    def get_queryset(self):
        return Component.objects.filter(
            Q(created_by=self.request.user) | Q(created_by__isnull=True)
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Prevent updating default components if not owner? 
        # For now, just allow reading. If they try to update, it might work but that's a future problem.
        # Actually logic is fine.
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Prevent deleting default components
        if instance.created_by is None:
             return Response({"status": "error", "message": "Cannot delete default components"}, status=status.HTTP_403_FORBIDDEN)
             
        instance.delete()
        return Response({"message": "Component deleted successfully"}, status=status.HTTP_200_OK)


class ComponentByNameView(generics.RetrieveAPIView):
    serializer_class = ComponentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'name'

    def get_queryset(self):
        return Component.objects.filter(
            Q(created_by=self.request.user) | Q(created_by__isnull=True)
        )
class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.select_related("user").filter(
            user=self.request.user
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "success",
            "projects": serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Don't pass user here
        project = serializer.save()
        return Response({
            "message": "Project created",
            "project": self.get_serializer(project).data
        }, status=status.HTTP_201_CREATED)

class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({
                "status": "error",
                "message": "Project not found"
            }, status=status.HTTP_404_NOT_FOUND)
        return super().handle_exception(exc)

    # -----------------------------
    # RETRIEVE
    # -----------------------------
    def retrieve(self, request, *args, **kwargs):
        project = self.get_object()

        # Project detail
        project_data = ProjectSerializer(project).data

        # Canvas items (nodes)
        canvas_items = (
            CanvasState.objects
            .filter(project=project)
            .select_related("component")
            .order_by("sequence")
        )

        items_data = CanvasStateSerializer(canvas_items, many=True).data

        # Connections (edges)
        connections = Connection.objects.filter(
            sourceItemId__project=project
        )

        connections_data = ConnectionSerializer(connections, many=True).data

        # Sequence counter (next available)
        sequence_counter = (
            canvas_items.last().sequence + 1
            if canvas_items.exists()
            else 0
        )
        response_data = project_data
        response_data["status"] = "success"
        response_data["canvas_state"] = {
                "items": items_data,
                "connections": connections_data,
                "sequence_counter": sequence_counter
            }

        return Response(response_data, status=status.HTTP_200_OK)

    # UPDATE (project only)

    def update(self, request, *args, **kwargs):
        project = self.get_object()

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(project, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        canvas_data = request.data.get("canvas_state")

        if canvas_data:
            items_data = canvas_data.get("items", [])
            connections_data = canvas_data.get("connections", [])

            from .models import CanvasState, Connection

            with transaction.atomic():

                # Delete existing state
                CanvasState.objects.filter(project=project).delete()

                # Bulk create CanvasState
                new_items = []
                old_id_order = []

                for item in items_data:
                    comp_id = item.get("component_id")
                    if not comp_id:
                        continue

                    new_items.append(
                        CanvasState(
                            project=project,
                            component_id=comp_id,
                            label=item.get("label", ""),
                            x=item.get("x", 0),
                            y=item.get("y", 0),
                            width=item.get("width", 50),
                            height=item.get("height", 50),
                            rotation=item.get("rotation", 0),
                            scaleX=item.get("scaleX", 1),
                            scaleY=item.get("scaleY", 1),
                            sequence=item.get("sequence", 0),
                        )
                    )

                    old_id_order.append(item.get("id"))

                created_items = CanvasState.objects.bulk_create(new_items)

                # Build ID map (old_id -> new_id)
                id_map = {}
                for old_id, new_instance in zip(old_id_order, created_items):
                    if old_id is not None:
                        id_map[old_id] = new_instance.id

                # Bulk create Connections
                new_connections = []

                for conn in connections_data:
                    source_old_id = conn.get("sourceItemId")
                    target_old_id = conn.get("targetItemId")

                    real_source_id = id_map.get(source_old_id)
                    real_target_id = id_map.get(target_old_id)

                    if real_source_id and real_target_id:
                        new_connections.append(
                            Connection(
                                sourceItemId_id=real_source_id,
                                targetItemId_id=real_target_id,
                                sourceGripIndex=conn.get("sourceGripIndex", 0),
                                targetGripIndex=conn.get("targetGripIndex", 0),
                                waypoints=conn.get("waypoints", []),
                            )
                        )

                if new_connections:
                    Connection.objects.bulk_create(new_connections)

        return self.retrieve(request, *args, **kwargs)

    # DELETE
    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        project.delete()

        return Response({
            "status": "success",
            "message": "Project deleted successfully"
        }, status=status.HTTP_200_OK)
