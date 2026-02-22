from django.contrib import admin

from .models import PredictionHistory


@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    """Administration des prédictions de sentiment."""
    list_display = ('query_short', 'sentiment', 'score', 'created_at')
    list_filter = ('sentiment', 'created_at')
    search_fields = ('query',)
    ordering = ('-created_at',)

    @admin.display(description='Requête')
    def query_short(self, obj):
        return obj.query[:60] + '…' if len(obj.query) > 60 else obj.query
