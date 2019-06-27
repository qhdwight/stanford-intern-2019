from django.contrib import admin

from .models import Log, Item, QueryCountAtTime

admin.site.register([Log, Item, QueryCountAtTime])
