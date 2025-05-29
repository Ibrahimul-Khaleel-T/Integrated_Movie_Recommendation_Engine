from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class UserInfo(AbstractUser):
    fullname=models.CharField(max_length=100)
    mobile_number=models.CharField(max_length=10)
    dp=models.FileField(null=True,blank=True)
    
