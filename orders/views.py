from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Sum, F, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Order
from .forms import OrderForm
from customers.models import Customer
from products.models import Product, Color, Size


class OrderListView(ListView):
    model = Order
    template_name = 'orders/list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_paginate_by(self, queryset):
        """Disable pagination when grouping to show full grouped summary."""
        group_by = (self.request.GET.get('group_by') or '').strip()
        if group_by in ['customer', 'product']:
            return None
        return super().get_paginate_by(queryset)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Support both 'q' and 'search' as query params
        search_query = (self.request.GET.get('q') or self.request.GET.get('search') or '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(code__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(customer__code__icontains=search_query) |
                Q(customer__phone_number__icontains=search_query) |
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(status__icontains=search_query) |
                Q(note__icontains=search_query)
            )
        statuses = self.request.GET.getlist('status')
        if statuses:
            queryset = queryset.filter(status__in=statuses)
        # Supplier filter (multi-select)
        supplier_ids = self.request.GET.getlist('supplier')
        if supplier_ids:
            queryset = queryset.filter(product__supplier_id__in=supplier_ids)
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        from django.db.models import F, FloatField, IntegerField, ExpressionWrapper, Case, When, Value
        from django.db.models.functions import Coalesce

        queryset = queryset.select_related('customer', 'product', 'color', 'size')
        queryset = queryset.annotate(
            amount_safe=Coalesce(F('amount'), 0, output_field=IntegerField()),
            price_safe=Coalesce(F('sale_price'), 0.0, output_field=FloatField()),
        )
        # Zero-out discount and revenue for cancelled orders
        queryset = queryset.annotate(
            discount_raw=Coalesce(F('discount'), 0.0, output_field=FloatField()),
        )
        queryset = queryset.annotate(
            revenue_raw=ExpressionWrapper(F('amount_safe') * F('price_safe'), output_field=FloatField()),
        )
        queryset = queryset.annotate(
            discount_safe=Case(
                When(status='cancelled', then=Value(0.0)),
                default=F('discount_raw'),
                output_field=FloatField(),
            ),
            revenue=Case(
                When(status='cancelled', then=Value(0.0)),
                default=F('revenue_raw'),
                output_field=FloatField(),
            ),
        ).annotate(
            net_profit=ExpressionWrapper(F('revenue') - F('discount_safe'), output_field=FloatField())
        )
        # Sorting
        sort = self.request.GET.get('sort')
        if sort == 'revenue_asc':
            queryset = queryset.order_by('revenue', '-created_at')
        elif sort == 'revenue_desc':
            queryset = queryset.order_by('-revenue', '-created_at')
        elif sort == 'created_asc':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add status choices to context for filter dropdown
        context['status_choices'] = dict(Order.STATUS_CHOICES)
        # Suppliers list for filter
        try:
            from suppliers.models import Supplier
            suppliers_qs = Supplier.objects.all()
            context['suppliers'] = suppliers_qs
        except Exception:
            context['suppliers'] = []
        
        # Add search query to context (prefer 'q')
        context['search_query'] = self.request.GET.get('q', self.request.GET.get('search', ''))
        context['sort'] = self.request.GET.get('sort', 'created_desc')
        context['status_filter'] = self.request.GET.getlist('status')
        # Supplier filter list (no strict validation here; UI controls input)
        context['supplier_filter'] = self.request.GET.getlist('supplier')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        # Display mode (table or card)
        display = self.request.GET.get('display', 'table')
        if display not in ['table', 'card']:
            display = 'table'
        context['display'] = display
        # Build querystring to forward filters to detail pages
        try:
            from urllib.parse import urlencode
            parts = []
            for s in self.request.GET.getlist('status'):
                parts.append(('status', s))
            for s in self.request.GET.getlist('supplier'):
                parts.append(('supplier', s))
            for key in ['q', 'search', 'sort', 'date_from', 'date_to']:
                val = (self.request.GET.get(key) or '').strip()
                if val:
                    parts.append((key, val))
            context['filters_qs'] = urlencode(parts, doseq=True)
        except Exception:
            context['filters_qs'] = ''
        
        # Group by support
        group_by = (self.request.GET.get('group_by') or '').strip()
        context['group_by'] = group_by if group_by in ['customer', 'product'] else ''
        
        # Totals for the entire filtered list (not just current page)
        try:
            from django.db.models import FloatField, IntegerField, ExpressionWrapper, Case, When, Value
            from django.db.models.functions import Coalesce
            qs = self.get_queryset().annotate(
                amount_safe=Coalesce(F('amount'), 0, output_field=IntegerField()),
                price_safe=Coalesce(F('product__price'), 0.0, output_field=FloatField()),
            ).annotate(
                discount_raw=Coalesce(F('discount'), 0.0, output_field=FloatField()),
                revenue_raw=ExpressionWrapper(F('amount_safe') * F('price_safe'), output_field=FloatField()),
            ).annotate(
                discount_safe=Case(
                    When(status='cancelled', then=Value(0.0)),
                    default=F('discount_raw'),
                    output_field=FloatField(),
                ),
                revenue=Case(
                    When(status='cancelled', then=Value(0.0)),
                    default=F('revenue_raw'),
                    output_field=FloatField(),
                ),
            )
            agg = qs.aggregate(
                order_count=Count('id'),
                total_amount=Coalesce(Sum('amount_safe'), 0),
                total_revenue=Coalesce(Sum('revenue'), 0.0),
                total_discount=Coalesce(Sum('discount_safe'), 0.0),
            )
            total_net_profit = (agg.get('total_revenue') or 0) - (agg.get('total_discount') or 0)
            context['list_totals'] = {
                'order_count': agg.get('order_count') or 0,
                'total_amount': agg.get('total_amount') or 0,
                'total_revenue': agg.get('total_revenue') or 0,
                'total_discount': agg.get('total_discount') or 0,
                'total_net_profit': total_net_profit,
            }
        except Exception:
            context['list_totals'] = {
                'order_count': 0,
                'total_amount': 0,
                'total_revenue': 0,
                'total_discount': 0,
                'total_net_profit': 0,
            }
        
        # Build grouped results if requested
        if context['group_by']:
            try:
                from django.db.models import FloatField, Min, Max
                from django.db.models import Sum as DJSum
                qs_group = self.get_queryset()
                if context['group_by'] == 'customer':
                    grouped = (
                        qs_group
                        .values('customer_id', 'customer__name', 'customer__code', 'customer__phone_number')
                        .annotate(
                            order_count=Count('id'),
                            total_amount=DJSum('amount_safe'),
                            total_revenue=DJSum('revenue'),
                            total_discount=DJSum('discount_safe'),
                            oldest=Min('created_at'),
                            newest=Max('created_at'),
                        )
                    )
                else:  # product
                    grouped = (
                        qs_group
                        .values('product_id', 'product__name', 'product__code', 'product__image', 'product__supplier__name')
                        .annotate(
                            order_count=Count('id'),
                            total_amount=DJSum('amount_safe'),
                            total_revenue=DJSum('revenue'),
                            total_discount=DJSum('discount_safe'),
                            oldest=Min('created_at'),
                            newest=Max('created_at'),
                        )
                    )
                # Order grouped results based on selected sort
                sort = self.request.GET.get('sort') or 'created_desc'
                if sort == 'revenue_asc':
                    grouped = grouped.order_by('total_revenue', '-newest')
                elif sort == 'revenue_desc':
                    grouped = grouped.order_by('-total_revenue', '-newest')
                elif sort == 'created_asc':
                    # Oldest order in group first
                    grouped = grouped.order_by('oldest', 'product_id' if context['group_by']=='product' else 'customer_id')
                else:  # created_desc or default
                    # Newest order in group first
                    grouped = grouped.order_by('-newest', 'product_id' if context['group_by']=='product' else 'customer_id')
                # compute net profit per group
                grouped_list = []
                for g in grouped:
                    g = dict(g)
                    g['total_net_profit'] = (g.get('total_revenue') or 0) - (g.get('total_discount') or 0)
                    grouped_list.append(g)
                context['grouped_results'] = grouped_list
            except Exception:
                context['grouped_results'] = []
        
        return context


class OrderCreateView(CreateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/create.html'
    success_url = reverse_lazy('orders:order_list')
    
    def get_initial(self):
        initial = super().get_initial()
        cust_param = self.request.GET.get('customer')
        prod_param = self.request.GET.get('product')
        # Prefill customer by code or id
        if cust_param:
            try:
                customer = Customer.objects.filter(code=cust_param).first() or Customer.objects.filter(id=int(cust_param)).first()
                if customer:
                    initial['customer'] = customer.pk
            except Exception:
                pass
        # Prefill product by id or code
        if prod_param:
            try:
                product = Product.objects.filter(id=int(prod_param)).first() or Product.objects.filter(code=prod_param).first()
                if product:
                    initial['product'] = product.pk
            except Exception:
                product = Product.objects.filter(code=prod_param).first()
                if product:
                    initial['product'] = product.pk
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Tạo đơn hàng mới - NavyBaby'
        # Show multi-line UI when coming from customer detail
        context['prefilled_customer'] = bool(self.request.GET.get('customer'))
        context['multi'] = bool(self.request.GET.get('multi'))
        return context
    
    def post(self, request, *args, **kwargs):
        # Handle multi mode before form validation
        if request.POST.get('multi'):
            self.object = None
            form = self.get_form()
            # Proceed with custom multi create irrespective of form validity for product/amount
            return self._handle_multi_create(form)
        return super().post(request, *args, **kwargs)

    def _handle_multi_create(self, form):
        # Multi mode: create multiple orders from items-* fields
        import logging
        logger = logging.getLogger(__name__)
        
        created = 0
        errors = []
        
        # Debug: log all POST data
        logger.info(f"Multi-create POST keys: {list(self.request.POST.keys())}")
        logger.info(f"items-count: {self.request.POST.get('items-count')}")
        
        customer_id = self.request.POST.get('customer')
        logger.info(f"Customer ID from POST: {customer_id}")
        try:
            customer = Customer.objects.get(id=int(customer_id)) if customer_id else None
        except (ValueError, Customer.DoesNotExist):
            customer = None
        if not customer:
            messages.error(self.request, 'Vui lòng chọn khách hàng hợp lệ.')
            logger.error("No valid customer found")
            return super().form_invalid(form)

        # Prefer an explicit count provided by the client
        count_val = self.request.POST.get('items-count')
        logger.info(f"Items count value: {count_val}")
        if count_val is not None:
            try:
                total = int(count_val)
                logger.info(f"Using explicit count: {total}")
            except ValueError:
                total = 0
                logger.warning(f"Invalid items-count value: {count_val}")
            indices = range(total)
        else:
            # Fallback: iterate until a missing key encountered
            logger.info("No items-count, using fallback probe")
            indices = None
        if indices is None:
            index = 0
            while True:
                p_key = f'items-{index}-product'
                if p_key not in self.request.POST:
                    break
                prod_val = (self.request.POST.get(p_key) or '').strip()
                if not prod_val:
                    index += 1
                    continue
                try:
                    product = Product.objects.get(id=int(prod_val))
                except (ValueError, Product.DoesNotExist):
                    errors.append(f'Hàng {index+1}: Sản phẩm không hợp lệ')
                    index += 1
                    continue

                # amount
                amount_raw = self.request.POST.get(f'items-{index}-amount')
                if amount_raw is None or str(amount_raw).strip() == '':
                    amount = 1
                else:
                    try:
                        amount = int(amount_raw)
                    except ValueError:
                        amount = 1
                # discount
                try:
                    discount = float(self.request.POST.get(f'items-{index}-discount') or 0)
                except ValueError:
                    discount = 0.0
                # sale_price (optional, default to product.price)
                try:
                    sale_price = int(float(self.request.POST.get(f'items-{index}-sale_price') or 0))
                except ValueError:
                    sale_price = 0
                # color/size optional
                color_id = self.request.POST.get(f'items-{index}-color') or ''
                size_id = self.request.POST.get(f'items-{index}-size') or ''
                color = None
                size = None
                if color_id:
                    try:
                        color = Color.objects.get(id=int(color_id))
                    except (ValueError, Color.DoesNotExist):
                        color = None
                if size_id:
                    try:
                        size = Size.objects.get(id=int(size_id))
                    except (ValueError, Size.DoesNotExist):
                        size = None

                if amount <= 0:
                    errors.append(f'Hàng {index+1}: Số lượng phải lớn hơn 0')
                    index += 1
                    continue

                if sale_price <= 0:
                    try:
                        sale_price = int(product.price)
                    except Exception:
                        sale_price = 0
                order = Order(customer=customer, product=product, amount=amount, discount=discount or 0, sale_price=sale_price)
                if color:
                    order.color = color
                if size:
                    order.size = size
                # default status
                order.status = 'created'
                order.save()
                created += 1
                index += 1
        else:
            for index in indices:
                p_key = f'items-{index}-product'
                prod_val = (self.request.POST.get(p_key) or '').strip()
                if not prod_val:
                    continue
                try:
                    product = Product.objects.get(id=int(prod_val))
                except (ValueError, Product.DoesNotExist):
                    errors.append(f'Hàng {index+1}: Sản phẩm không hợp lệ')
                    continue

                # amount
                amount_raw = self.request.POST.get(f'items-{index}-amount')
                if amount_raw is None or str(amount_raw).strip() == '':
                    amount = 1
                else:
                    try:
                        amount = int(amount_raw)
                    except ValueError:
                        amount = 1
                # discount
                try:
                    discount = float(self.request.POST.get(f'items-{index}-discount') or 0)
                except ValueError:
                    discount = 0.0
                # sale_price (optional, default to product.price)
                try:
                    sale_price = int(float(self.request.POST.get(f'items-{index}-sale_price') or 0))
                except ValueError:
                    sale_price = 0
                # color/size optional
                color_id = self.request.POST.get(f'items-{index}-color') or ''
                size_id = self.request.POST.get(f'items-{index}-size') or ''
                color = None
                size = None
                if color_id:
                    try:
                        color = Color.objects.get(id=int(color_id))
                    except (ValueError, Color.DoesNotExist):
                        color = None
                if size_id:
                    try:
                        size = Size.objects.get(id=int(size_id))
                    except (ValueError, Size.DoesNotExist):
                        size = None

                if amount <= 0:
                    errors.append(f'Hàng {index+1}: Số lượng phải lớn hơn 0')
                    continue

                if sale_price <= 0:
                    try:
                        sale_price = int(product.price)
                    except Exception:
                        sale_price = 0
                order = Order(customer=customer, product=product, amount=amount, discount=discount or 0, sale_price=sale_price)
                if color:
                    order.color = color
                if size:
                    order.size = size
                order.status = 'created'
                order.save()
                logger.info(f"Created order {order.code} for product {product.name}")
                created += 1

        logger.info(f"Total orders created: {created}")
        logger.info(f"Errors encountered: {errors}")
        
        if created:
            if errors:
                messages.warning(self.request, f'Đã tạo {created} đơn hàng. Một số dòng bị lỗi và đã bị bỏ qua.')
            else:
                messages.success(self.request, f'Đã tạo {created} đơn hàng thành công!')
            # In multi mode, go back to customer detail
            try:
                return redirect('customers:customer_detail', customer.code)
            except Exception:
                return redirect(self.success_url)

        # No orders created
        if errors:
            for e in errors:
                messages.error(self.request, e)
        else:
            messages.error(self.request, 'Không có sản phẩm nào được thêm vào. Vui lòng chọn ít nhất một sản phẩm.')
        logger.warning("No orders created, returning to form")
        return super().form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Vui lòng kiểm tra lại thông tin.')
        return super().form_invalid(form)


class OrderUpdateView(UpdateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/create.html'
    
    def get_success_url(self):
        return reverse_lazy('orders:order_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cập nhật đơn hàng - NavyBaby'
        context['action'] = 'update'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Cập nhật đơn hàng thành công!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Vui lòng kiểm tra lại thông tin.')
        return super().form_invalid(form)


class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        price = order.product.price if order.product and order.product.price is not None else 0
        amount = order.amount or 0
        discount = order.discount or 0.0
        context['revenue'] = amount * price - discount

        # Customer statistics for mini cards
        customer = getattr(order, 'customer', None)
        if customer:
            stats_qs = Order.objects.filter(customer=customer).select_related('product')
            order_count = stats_qs.count()
            total_discount_val = 0
            revenue_val = 0
            for o in stats_qs:
                total_discount_val += (o.discount or 0)
                p = o.product.price if (o.product and o.product.price is not None) else 0
                revenue_val += (o.amount or 0) * p
            net_profit_val = revenue_val - total_discount_val

            context['customer_stats'] = {
                'order_count': order_count,
                'revenue': revenue_val,
                'net_profit': net_profit_val,
                'total_discount': total_discount_val,
            }

        # Product statistics for mini cards
        product = getattr(order, 'product', None)
        if product:
            p_stats_qs = Order.objects.filter(product=product).select_related('product')
            p_order_count = p_stats_qs.count()
            p_total_discount = 0
            p_revenue = 0
            for o in p_stats_qs:
                p_total_discount += (o.discount or 0)
                unit_price = o.product.price if (o.product and o.product.price is not None) else 0
                p_revenue += (o.amount or 0) * unit_price
            p_net_profit = p_revenue - p_total_discount

            context['product_stats'] = {
                'order_count': p_order_count,
                'revenue': p_revenue,
                'net_profit': p_net_profit,
                'total_discount': p_total_discount,
            }
        return context


class OrderDeleteView(DeleteView):
    model = Order
    success_url = reverse_lazy('orders:order_list')
    template_name = 'orders/confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Đã xóa đơn hàng thành công!')
        return super().delete(request, *args, **kwargs)


@require_http_methods(["POST"])
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    next_url = request.POST.get('next') or ''
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()
        messages.success(request, f'Đã cập nhật trạng thái đơn hàng thành "{dict(Order.STATUS_CHOICES)[new_status]}"')
    else:
        messages.error(request, 'Trạng thái không hợp lệ')
    # Redirect back to originating page if safe relative path provided
    if next_url.startswith('/'):
        return redirect(next_url)
    return redirect('orders:order_detail', pk=order.pk)


def get_product_details(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        colors = [{'id': c.id, 'name': c.name} for c in product.colors.all()]
        sizes = [{'id': s.id, 'name': s.name} for s in product.sizes.all()]
        # Safe image URL handling for local/dev without Cloudinary config
        image_url = ''
        if product.image:
            try:
                image_url = product.image.url
            except Exception:
                name = getattr(product.image, 'name', '')
                if name:
                    from django.conf import settings
                    base = getattr(settings, 'MEDIA_URL', '/media/')
                    if not base.endswith('/'):
                        base += '/'
                    image_url = f"{base}{name}"

        return JsonResponse({
            'success': True,
            'colors': colors,
            'sizes': sizes,
            'price': str(product.price),
            'code': product.code,
            'supplier': product.supplier.name if product.supplier else '',
            'image_url': image_url
        })
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'})


@require_http_methods(["POST"])
def bulk_update_order_status(request):
    ids = request.POST.getlist('order_ids')
    new_status = request.POST.get('status')
    next_url = request.POST.get('next') or ''
    # Only allow relative paths for safety
    redirect_target = 'orders:order_list'
    if next_url.startswith('/'):
        # keep querystring to re-render same state
        return_to = next_url
    else:
        return_to = None
    if not ids:
        messages.warning(request, 'Vui lòng chọn ít nhất một đơn hàng.')
        return redirect(return_to or redirect_target)
    valid_statuses = dict(Order.STATUS_CHOICES)
    if new_status not in valid_statuses:
        messages.error(request, 'Trạng thái không hợp lệ')
        return redirect(return_to or redirect_target)
    try:
        updated = Order.objects.filter(id__in=ids).update(status=new_status)
        messages.success(request, f'Đã cập nhật trạng thái {updated} đơn hàng.')
    except Exception:
        messages.error(request, 'Không thể cập nhật trạng thái. Vui lòng thử lại.')
    return redirect(return_to or redirect_target)
