import pycountry
from django import forms

COUNTRIES = sorted([(country.name, country.name) for country in pycountry.countries])


class ChartForm(forms.Form):
    country = forms.ChoiceField(choices=COUNTRIES, initial='India')
    kind = forms.ChoiceField(choices=[('artists', 'Top artists'), ('tracks', 'Top tracks')])
    page = forms.IntegerField(min_value=1, max_value=1000, initial=1, required=False, widget=forms.HiddenInput)

    def clean_page(self):
        return self.cleaned_data.get('page') or 1


class SearchForm(forms.Form):
    q = forms.CharField(label='Search for', min_length=2, max_length=120)
    kind = forms.ChoiceField(choices=[('artist', 'Artists'), ('album', 'Albums'), ('track', 'Tracks')])
    page = forms.IntegerField(min_value=1, max_value=1000, initial=1, required=False, widget=forms.HiddenInput)

    def clean_page(self):
        return self.cleaned_data.get('page') or 1


class PassportForm(forms.Form):
    home = forms.ChoiceField(label='Home country', choices=COUNTRIES, initial='India')
    destination = forms.ChoiceField(label='Destination country', choices=COUNTRIES, initial='Japan')

    def clean(self):
        data = super().clean()
        if data.get('home') and data.get('home') == data.get('destination'):
            raise forms.ValidationError('Choose two different countries for your journey.')
        return data
