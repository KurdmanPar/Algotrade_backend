# apps/instruments/views.py
from rest_framework import viewsets, permissions
from .models import (
    InstrumentGroup,
    InstrumentCategory,
    Instrument,
    InstrumentExchangeMap,
    IndicatorGroup,
    Indicator,
    IndicatorParameter,
    IndicatorTemplate,
    PriceActionPattern,
    SmartMoneyConcept,
    AIMetric
)
from .serializers import *
from apps.core.views import SecureModelViewSet


class InstrumentGroupViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = InstrumentGroup.objects.all()
    serializer_class = InstrumentGroupSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class InstrumentCategoryViewSet(viewsets.ModelViewSet):
    queryset = InstrumentCategory.objects.all()
    serializer_class = InstrumentCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class InstrumentViewSet(viewsets.ModelViewSet):
    queryset = Instrument.objects.all()
    serializer_class = InstrumentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class InstrumentExchangeMapViewSet(viewsets.ModelViewSet):
    queryset = InstrumentExchangeMap.objects.all()
    serializer_class = InstrumentExchangeMapSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class IndicatorGroupViewSet(viewsets.ModelViewSet):
    queryset = IndicatorGroup.objects.all()
    serializer_class = IndicatorGroupSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class IndicatorViewSet(viewsets.ModelViewSet):
    queryset = Indicator.objects.all()
    serializer_class = IndicatorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class IndicatorParameterViewSet(viewsets.ModelViewSet):
    queryset = IndicatorParameter.objects.all()
    serializer_class = IndicatorParameterSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class IndicatorTemplateViewSet(viewsets.ModelViewSet):
    queryset = IndicatorTemplate.objects.all()
    serializer_class = IndicatorTemplateSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class PriceActionPatternViewSet(viewsets.ModelViewSet):
    queryset = PriceActionPattern.objects.all()
    serializer_class = PriceActionPatternSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class SmartMoneyConceptViewSet(viewsets.ModelViewSet):
    queryset = SmartMoneyConcept.objects.all()
    serializer_class = SmartMoneyConceptSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class AIMetricViewSet(viewsets.ModelViewSet):
    queryset = AIMetric.objects.all()
    serializer_class = AIMetricSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]