from django.views.generic import TemplateView


class AboutPage(TemplateView):
    template_name = 'about/author.html'


class TechPage(TemplateView):
    template_name = 'about/tech.html'
