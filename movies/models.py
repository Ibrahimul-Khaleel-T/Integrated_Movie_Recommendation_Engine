from django.db import models
from users.models import UserInfo

# Create your models here.

class Review(models.Model):
    user=models.ForeignKey(UserInfo,on_delete=models.CASCADE)
    movie_id=models.IntegerField()
    rating=models.PositiveIntegerField(default=1)
    comment=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} - {self.rating} stars"
