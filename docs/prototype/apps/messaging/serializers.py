from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "article", "sender", "sender_name", "sender_role",
                  "recipient", "body", "created_at"]
        read_only_fields = ["id", "sender", "sender_name", "sender_role", "created_at"]
