from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.CharField("JavaScript UUID", unique=True, null=False, blank=False)
    conv_id = models.CharField("OpenAI Conversation ID", unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # messages = models.TextField("Conversation History")
    
    # the files field might need to be changed to TextField to only store names of the files
    files = models.TextField("Uploaded Files", null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.user.username