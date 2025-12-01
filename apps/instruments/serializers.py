# apps/instruments/serializers.py
from rest_framework import serializers
from .models import (
    InstrumentGroup, InstrumentCategory, Instrument, InstrumentExchangeMap,
    IndicatorGroup, Indicator, IndicatorParameter, IndicatorTemplate,
    PriceActionPattern, SmartMoneyConcept, AIMetric
)


class InstrumentGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentGroup
        fields = '__all__'


class InstrumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentCategory
        fields = '__all__'


class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = '__all__'


class InstrumentExchangeMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentExchangeMap
        fields = '__all__'


class IndicatorGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorGroup
        fields = '__all__'


class IndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = '__all__'


class IndicatorParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorParameter
        fields = '__all__'


class IndicatorTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorTemplate
        fields = '__all__'


class PriceActionPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceActionPattern
        fields = '__all__'


class SmartMoneyConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartMoneyConcept
        fields = '__all__'


class AIMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMetric
        fields = '__all__'