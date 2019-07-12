from django.contrib import admin

from .models import Log, Item, QueryCountAtTime, Experiment, Lab, Award

# This allows us to browse the models in our admin site
admin.site.register([Log, Item, QueryCountAtTime, Experiment, Lab, Award])
