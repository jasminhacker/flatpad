from django.db import models


class Pad(models.Model):
    version = models.IntegerField(default=0)
    content = models.CharField(max_length=100000)

    def __str__(self) -> str:
        return f"{self.content[:20]}... ({self.version})"


class Presence(models.Model):
    mac = models.CharField(max_length=100, unique=True)
    present = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.mac}: {self.present}"


class Anonymous(models.Model):
    count = models.IntegerField(default=0)

    def __str__(self):
        return f"Anonymous: {self.count}"


class LastCheck(models.Model):
    performed = models.DateTimeField(auto_now=True)
