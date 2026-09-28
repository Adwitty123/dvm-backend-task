from urllib.parse import urlencode
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from .forms import ChartForm, PassportForm, SearchForm
from .services import LastFMClient, LastFMError, build_passport


def wants_json(request):
    return request.GET.get('format') == 'json'


def listing(request, form_class, template, fetch):
    form = form_class(request.GET if request.GET else None)
    context = {'form': form}
    status = 200
    if request.GET:
        if form.is_valid():
            try:
                result = fetch(form.cleaned_data)
                if wants_json(request):
                    return JsonResponse(result)
                context['result'] = result
                for label, page in [('previous', result['page'] - 1), ('next', result['page'] + 1)]:
                    params = request.GET.copy()
                    params['page'] = page
                    context[f'{label}_query'] = params.urlencode()
            except LastFMError as exc:
                status = exc.status
                context['error'] = str(exc)
        else:
            status = 400
        if wants_json(request):
            return JsonResponse({'error': context.get('error', 'Invalid parameters.'), 'fields': form.errors.get_json_data()}, status=status)
    return render(request, template, context, status=status)


@require_GET
def charts(request):
    return listing(request, ChartForm, 'music/charts.html', lambda data: LastFMClient().charts(data['country'], data['kind'], data['page']))


@require_GET
def search(request):
    return listing(request, SearchForm, 'music/search.html', lambda data: LastFMClient().search(data['q'], data['kind'], data['page']))


@require_GET
def passport(request):
    form = PassportForm(request.GET if request.GET else None)
    context = {'form': form}
    status = 200
    if request.GET:
        if form.is_valid():
            try:
                report = build_passport(**form.cleaned_data)
                if wants_json(request) or request.GET.get('download') == '1':
                    response = JsonResponse(report, json_dumps_params={'indent': 2, 'ensure_ascii': False})
                    if request.GET.get('download') == '1':
                        response['Content-Disposition'] = 'attachment; filename="music-passport.json"'
                    return response
                context['report'] = report
                context['download_query'] = urlencode({**form.cleaned_data, 'download': '1'})
            except LastFMError as exc:
                status = exc.status
                context['error'] = str(exc)
        else:
            status = 400
        if wants_json(request) or request.GET.get('download') == '1':
            return JsonResponse({'error': context.get('error', 'Invalid parameters.'), 'fields': form.errors.get_json_data()}, status=status)
    return render(request, 'music/passport.html', context, status=status)
