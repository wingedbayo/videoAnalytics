from django.contrib import admin
from .models import Chat

# Register your models here.
class ChatAdmin(admin.ModelAdmin):
    list_display = ["user", "uuid", "conv_id", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    
admin.site.register(Chat, ChatAdmin)
