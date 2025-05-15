from django.db import models

class User(models.Model):
    name = models.CharField(max_length=150, unique=True, help_text="User's name")
    password = models.CharField(max_length=128)

    def __str__(self):
        return f"USER name: {self.name}"

class Conversation(models.Model):
    user_id = models.IntegerField(default=-1, help_text="ID of the user this conversation belongs to")

    def __str__(self):
        return f"Conversation {self.id} (User ID {self.user_id})"

class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    index = models.PositiveIntegerField(help_text="Message order in the conversation")

    class Meta:
        unique_together = ('conversation', 'index')
        ordering = ['index']

    def __str__(self):
        return f"{self.role} message #{self.index} in conversation {self.conversation.id}"

from django.utils import timezone  # 可选，供后续拓展使用

class OpenPost(models.Model):
    id = models.AutoField(primary_key=True)
    post_owner_name = models.CharField(max_length=100)
    post_title = models.CharField(max_length=200)
    post_content = models.TextField()
    travel_place = models.CharField(max_length=100, default="")  # 旅行地点
    like_list = models.JSONField(default=list)  # 存储用户名的 list
    created_at = models.DateTimeField(default=timezone.now)  # 自动生成时间戳

    def __str__(self):
        return f"{self.post_title} by {self.post_owner_name}"
