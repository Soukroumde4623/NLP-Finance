from django.db import models

class PredictionHistory(models.Model):
    query = models.TextField()
    sentiment = models.CharField(max_length=20)
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sentiment} ({self.score:.2f}) - {self.created_at}"
