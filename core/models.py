from django.db import models

class Conversation(models.Model):
    # conversation_id 改成主键 ID 自动增长
    # 保持兼容前端传入 str 类型
    def __str__(self):
        return f"Conversation {self.id}"


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
