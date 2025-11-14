from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Supplier


class SupplierListView(ListView):
    model = Supplier
    template_name = 'suppliers/list.html'
    context_object_name = 'suppliers'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nhà cung cấp - NavyBaby'
        context['action'] = 'list'
        return context


class SupplierCreateView(CreateView):
    model = Supplier
    template_name = 'suppliers/list.html'
    fields = ['name', 'note']
    success_url = reverse_lazy('suppliers:supplier_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Thêm nhà cung cấp - NavyBaby'
        context['action'] = 'create'
        context['suppliers'] = Supplier.objects.all()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        base_classes = 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700'
        for field in form.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' ' + base_classes).strip()
        return form


class SupplierUpdateView(UpdateView):
    model = Supplier
    template_name = 'suppliers/list.html'
    fields = ['name', 'note']
    slug_field = 'code'
    slug_url_kwarg = 'code'
    success_url = reverse_lazy('suppliers:supplier_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cập nhật nhà cung cấp - NavyBaby'
        context['action'] = 'update'
        context['suppliers'] = Supplier.objects.all()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        base_classes = 'w-full bg-[#161616] border border-gray-800 rounded-md px-3 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-gray-700'
        for field in form.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' ' + base_classes).strip()
        return form


class SupplierDeleteView(DeleteView):
    model = Supplier
    template_name = 'suppliers/list.html'
    slug_field = 'code'
    slug_url_kwarg = 'code'
    success_url = reverse_lazy('suppliers:supplier_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Xóa nhà cung cấp - NavyBaby'
        context['action'] = 'delete'
        context['suppliers'] = Supplier.objects.all()
        return context