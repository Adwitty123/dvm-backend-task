from django.contrib import admin
from .models import Choice, Question


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3
    readonly_fields = ['votes']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    fieldsets = [(None, {'fields': ['question_text', 'author']}), ('Schedule', {'fields': ['pub_date', 'closes_at']})]
    inlines = [ChoiceInline]
    list_display = ['question_text', 'pub_date', 'closes_at', 'was_published_recently']
    list_filter = ['pub_date']
    search_fields = ['question_text']
