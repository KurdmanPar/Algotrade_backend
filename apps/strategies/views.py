# apps/strategies/views.py
from rest_framework import viewsets, permissions
from .models import Strategy, StrategyVersion, StrategyAssignment
from .serializers import StrategySerializer, StrategyVersionSerializer, StrategyAssignmentSerializer

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return True

class StrategyViewSet(viewsets.ModelViewSet):
    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Strategy.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class StrategyVersionViewSet(viewsets.ModelViewSet):
    queryset = StrategyVersion.objects.all()
    serializer_class = StrategyVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

class StrategyAssignmentViewSet(viewsets.ModelViewSet):
    queryset = StrategyAssignment.objects.all()
    serializer_class = StrategyAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]