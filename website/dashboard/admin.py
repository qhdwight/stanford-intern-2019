from django.contrib import admin

from .models import Log, Item

admin.site.register([Log, Item])
