from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Category


class CategoryListView(ListView):
    model = Category
    template_name = 'categories/list.html'
    context_object_name = 'categories'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Danh mục - NavyBaby'
        context['action'] = 'list'
        return context


class CategoryCreateView(CreateView):
    model = Category
    template_name = 'categories/list.html'
    fields = ['name', 'note']
    success_url = reverse_lazy('categories:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thêm danh mục - NavyBaby'
        context['action'] = 'create'
        context['categories'] = Category.objects.all()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        base_classes = 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700'
        for field in form.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' ' + base_classes).strip()
        return form


class CategoryUpdateView(UpdateView):
    model = Category
    template_name = 'categories/list.html'
    fields = ['name', 'note']
    slug_field = 'code'
    slug_url_kwarg = 'code'
    success_url = reverse_lazy('categories:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cập nhật danh mục - NavyBaby'
        context['action'] = 'update'
        context['categories'] = Category.objects.all()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        base_classes = 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700'
        for field in form.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' ' + base_classes).strip()
        return form


class CategoryDeleteView(DeleteView):
    model = Category
    template_name = 'categories/list.html'
    slug_field = 'code'
    slug_url_kwarg = 'code'
    success_url = reverse_lazy('categories:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Xóa danh mục - NavyBaby'
        context['action'] = 'delete'
        context['categories'] = Category.objects.all()
        return context
