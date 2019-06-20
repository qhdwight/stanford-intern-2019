from django.contrib import admin

from .models import Log, Item, MostQueried, IntervalQueryCount

admin.site.register([Log, Item, MostQueried, IntervalQueryCount])
