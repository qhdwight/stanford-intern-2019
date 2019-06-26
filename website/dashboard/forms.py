from django import forms

WIDGET = forms.widgets.DateInput(attrs={'type': 'date'})


class SelectTimeRangeForm(forms.Form):
    start_time = forms.DateTimeField(widget=WIDGET)
    end_time = forms.DateTimeField(widget=WIDGET)
