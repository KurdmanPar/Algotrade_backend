# apps/core/serializers.py
from rest_framework import serializers


class TimestampedModelSerializer(serializers.ModelSerializer):
    """
    سریالایزر پایه برای مدل‌هایی که created_at و updated_at دارند.
    """
    class Meta:
        abstract = True


class OwnedModelSerializer(TimestampedModelSerializer):
    """
    سریالایزر پایه برای مدل‌هایی که owner دارند.
    owner را در خروجی نشان می‌دهد، اما در ورودی به صورت خودکار از context پر می‌شود.
    """
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(TimestampedModelSerializer.Meta):
        abstract = True

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # جلوگیری از تغییر owner
        validated_data.pop('owner', None)
        return super().update(instance, validated_data)