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
