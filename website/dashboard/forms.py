from django import forms

WIDGET = forms.widgets.DateInput(attrs={'type': 'date'})


class SelectTimeRangeForm(forms.Form):
    start_time = forms.DateTimeField(widget=WIDGET)
    end_time = forms.DateTimeField(widget=WIDGET)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('start_time') > cleaned_data.get('end_time'):
            self.add_error('end_time', 'End time must be after start time!')
