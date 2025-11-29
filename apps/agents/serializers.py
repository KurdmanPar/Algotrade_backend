# apps/agents/serializers.py
from rest_framework import serializers
from .models import AgentType, Agent, AgentInstance, AgentConfig, AgentStatus, AgentMessage, AgentLog, AgentMetric

class AgentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentType
        fields = '__all__'

class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = '__all__'
        read_only_fields = ('owner', 'created_by')

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        validated_data['created_by'] = user
        return super().create(validated_data)

class AgentInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentInstance
        fields = '__all__'

class AgentConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentConfig
        fields = '__all__'

class AgentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentStatus
        fields = '__all__'

class AgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMessage
        fields = '__all__'

class AgentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentLog
        fields = '__all__'

class AgentMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMetric
        fields = '__all__'