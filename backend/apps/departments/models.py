from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=160, unique=True)
    code = models.SlugField(max_length=24, unique=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} ({self.code})'
