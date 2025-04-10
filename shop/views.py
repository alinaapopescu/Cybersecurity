from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.models import Group
from .models import Product, Order, OrderItem
from .forms import CheckoutForm, UserRegistrationForm, CommentForm


def product_list(request):
    products = Product.objects.all()
    return render(request, 'shop/product_list.html', {'products': products})


def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    # Retrieve comments for this product, ordered by most recent
    comments = product.comments.all().order_by('-created_at')
    message = ""
    comment_form = None

    # Determine if the current user has purchased this product.
    purchased = False
    if request.user.is_authenticated:
        # Look through the user's orders and check for the product in order items.
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
                # Redirect to avoid re-submission of the form.
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
    cart = request.session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session['cart'] = cart
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

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('shop:product_list')
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save()
            for product_id, quantity in cart.items():
                product = get_object_or_404(Product, pk=product_id)
                OrderItem.objects.create(order=order, product=product, quantity=quantity)
            # Clear the cart after order is placed
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
            # Assign user to the "customer" group
            customer_group, created = Group.objects.get_or_create(name='customer')
            user.groups.add(customer_group)
            login(request, user)
            return redirect('shop:product_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'shop/register.html', {'form': form})


import os
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import login as auth_login, get_user_model
from django.views.decorators.csrf import csrf_exempt


def custom_encode(s, shift=2):
    """
    Applies a simple Caesar cipher shifting letters by the given shift.
    Only shifts alphabetic characters; digits and punctuation remain unchanged.
    """

    def shift_char(c):
        if 'a' <= c <= 'z':
            return chr((ord(c) - ord('a') + shift) % 26 + ord('a'))
        elif 'A' <= c <= 'Z':
            return chr((ord(c) - ord('A') + shift) % 26 + ord('A'))
        else:
            return c

    return ''.join(shift_char(c) for c in s)


@csrf_exempt
def login(request):
    PREFIX = "XYZ"
    SUFFIX = "ABC"

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        reversed_username = username[::-1]
        reversed_password = password[::-1]

        encoded_username = custom_encode(reversed_username, shift=2)
        encoded_password = custom_encode(reversed_password, shift=2)

        final_username = PREFIX + encoded_username + SUFFIX
        final_password = PREFIX + encoded_password + SUFFIX

        query = ("SELECT id FROM auth_user WHERE username = '%s' AND password = '%s'" %
                 (final_username, final_password))

        cursor = connection.cursor()
        cursor.execute(query)
        row = cursor.fetchone()

        if row:
            User = get_user_model()
            try:
                user = User.objects.get(pk=row[0])
                auth_login(request, user)
                return HttpResponseRedirect('/')
            except User.DoesNotExist:
                pass
        return HttpResponse("Login failed")

    return render(request, 'registration/login.html')

