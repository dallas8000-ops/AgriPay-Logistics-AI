from django.db import models

from apps.accounts.models import User


class Notification(models.Model):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    body = models.TextField()
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


def send_notification(user, title, body, channel="in_app", metadata=None):
    """Create notification; SMS/WhatsApp logged for sandbox."""
    notif = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        channel=channel,
        metadata=metadata or {},
    )
    if channel in (Notification.Channel.SMS, Notification.Channel.WHATSAPP):
        notif.metadata["sandbox_sent"] = True
        notif.metadata["delivery_status"] = "simulated"
        notif.save(update_fields=["metadata"])
    return notif
