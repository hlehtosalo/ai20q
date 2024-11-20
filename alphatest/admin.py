from django.contrib import admin
from .models import Conversation, TargetWord, PlayerStats

class TargetWordAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)

admin.site.register(Conversation)
admin.site.register(TargetWord, TargetWordAdmin)
admin.site.register(PlayerStats)
