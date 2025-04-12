from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login as auth_login, get_user_model, logout as auth_logout
from django.contrib.auth.models import Group
from django.contrib import messages
from .models import Product, Order, OrderItem
from .forms import CheckoutForm, UserRegistrationForm, CommentForm

def product_list(request):
    products = Product.objects.all()
    return render(request, 'shop/product_list.html', {'products': products})

def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    comments = product.comments.all().order_by('-created_at')
    message = ""
    comment_form = None

    purchased = False
    if request.user.is_authenticated:
        orders = request.user.orders.all()
        for order in orders:
            if order.items.filter(product=product).exists():
                purchased = True
                break

    if request.method == 'POST':
        if not request.user.is_authenticated:
            message = "You must be logged in to comment."
        elif not purchased:
            message = "You can only comment if you have purchased this product."
        else:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.product = product
                comment.user = request.user
                comment.save()
                message = "Comment added successfully!"
                return redirect('shop:product_detail', product_id=product.id)
    else:
        if request.user.is_authenticated and purchased:
            comment_form = CommentForm()

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'comments': comments,
        'comment_form': comment_form,
        'message': message,
        'purchased': purchased,
    })



def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if product.stock == 0:
        messages.error(request, "Produsul nu este în stoc.")
        return redirect('shop:product_list')

    cart = request.session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session['cart'] = cart
    messages.success(request, f"{product.name} a fost adăugat în coș.")
    return redirect('shop:cart')


def cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)
        subtotal = product.price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal
        })
        total += subtotal

    return render(request, 'shop/cart.html', {'cart_items': cart_items, 'total': total})

def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        messages.success(request, "Produsul a fost șters din coș.")
    return redirect('shop:cart')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('shop:product_list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            total = 0
            for product_id, quantity in cart.items():
                product = get_object_or_404(Product, pk=product_id)

                if product.stock < quantity:
                    messages.error(request, f"Stoc insuficient pentru {product.name}.")
                    return redirect('shop:cart')

                product.stock -= quantity
                product.save()

                subtotal = product.price * quantity
                total += subtotal

                OrderItem.objects.create(order=order, product=product, quantity=quantity)

            if order.shipping_method == 'fast':
                total += 30
            elif order.shipping_method == 'standard':
                total += 15

            request.session['cart'] = {}

            send_mail(
                subject='Confirmarea comenzii tale - Simple Online Shop',
                message=(
                    f"Salut, {order.customer_name}!\n\n"
                    f"Îți mulțumim pentru comandă.\n\n"
                    f"Detalii comandă:\n"
                    f"- Total: {total} RON\n"
                    f"- Metodă de livrare: {order.get_shipping_method_display()}\n\n"
                    f"Comanda ta va fi procesată în curând!"
                ),
                from_email=None,  # Folosește DEFAULT_FROM_EMAIL
                recipient_list=[order.email],
                fail_silently=False,
            )
            return render(request, 'shop/checkout_success.html', {
                'order': order,
                'final_total': total
            })
    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {'form': form})


from .forms import CheckoutForm

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('shop:product_list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            for product_id, quantity in cart.items():
                product = get_object_or_404(Product, pk=product_id)

                if product.stock < quantity:
                    messages.error(request, f"Stoc insuficient pentru {product.name}.")
                    return redirect('shop:cart')

                product.stock -= quantity
                product.save()

                OrderItem.objects.create(order=order, product=product, quantity=quantity)

            request.session['cart'] = {}
            return render(request, 'shop/checkout_success.html', {'order': order})
    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            customer_group, created = Group.objects.get_or_create(name='customer')
            user.groups.add(customer_group)
            auth_login(request, user)
            return redirect('shop:product_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'shop/register.html', {'form': form})


from django.db import connection


def custom_encode(s, shift=2):
    """
    Applies a simple Caesar cipher shifting letters by the given shift.
    Only alphabetic characters are shifted; digits and punctuation remain unchanged.
    """
    def shift_char(c):
        if 'a' <= c <= 'z':
            return chr((ord(c) - ord('a') + shift) % 26 + ord('a'))
        elif 'A' <= c <= 'Z':
            return chr((ord(c) - ord('A') + shift) % 26 + ord('A'))
        else:
            return c
    return ''.join(shift_char(c) for c in s)

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        query = f"SELECT id, password FROM auth_user WHERE username = '{username}'"
        cursor = connection.cursor()
        cursor.execute(query)
        row = cursor.fetchone()

        if row:
            user_id, stored_password = row
            if check_password(password, stored_password):
                User = get_user_model()
                try:
                    user = User.objects.get(pk=user_id)
                    auth_login(request, user)
                    messages.success(request, 'You have been logged in successfully!')
                    return redirect('shop:product_list')
                except User.DoesNotExist:
                    messages.error(request, 'Login failed: user does not exist.')

        messages.error(request, 'Invalid username or password.')
        return render(request, 'registration/login.html')

    return render(request, 'registration/login.html')

def user_logout(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            auth_logout(request)
            messages.success(request, 'Logout Successful')
    return redirect('shop:product_list')


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'shop/order_detail.html', {'order': order})

@login_required
def my_orders(request):
    orders = request.user.orders.all().order_by('-created_at')
    return render(request, 'shop/my_orders.html', {'orders': orders})

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if product.stock == 0:
        messages.error(request, "Produsul nu este în stoc.")
        return redirect('shop:product_list')

    cart = request.session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session['cart'] = cart
    messages.success(request, f"{product.name} a fost adăugat în coș.")
    return redirect('shop:cart')


def increase_quantity(request, product_id):
    cart = request.session.get('cart', {})
    product = get_object_or_404(Product, pk=product_id)

    current_quantity = cart.get(str(product_id), 0)

    if product.stock > current_quantity:
        cart[str(product_id)] = current_quantity + 1
        request.session['cart'] = cart
    else:
        messages.error(request, f"Stoc insuficient pentru {product.name}.")

    return redirect('shop:cart')

def decrease_quantity(request, product_id):
    cart = request.session.get('cart', {})
    current_quantity = cart.get(str(product_id), 0)

    if current_quantity > 1:
        cart[str(product_id)] = current_quantity - 1
    elif current_quantity == 1:
        del cart[str(product_id)]
    else:
        messages.error(request, "Cantitate invalidă.")

    request.session['cart'] = cart
    return redirect('shop:cart')

@login_required
def my_orders(request):
    orders = request.user.orders.all().order_by('-created_at')
    return render(request, 'shop/my_orders.html', {'orders': orders})











