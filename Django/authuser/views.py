"""
Views for user authentication and profile management

Handles:
- User login and signup
- Profile editing (username, email)
- Password changes
- Account deletion
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from predict.models import PredictionHistory
from .forms import SignUpForm

def login_view(request):
    """Handle user authentication and login"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'authuser/login.html', {'form': form})

def signup_view(request):
    """Handle new user registration and account creation"""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created.')
            return redirect('home')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = SignUpForm()
    return render(request, 'authuser/signup.html', {'form': form})

def logout_view(request):
    """Log out current user and redirect to home page"""
    logout(request)
    return redirect('home')

@login_required
def edit_profile_view(request):
    """Allow users to update their username and email"""
    if request.method == 'POST':
        user = request.user
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        # Validate username is not already in use by another user
        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            messages.error(request, 'Username is already taken.')
            return render(request, 'authuser/edit_profile.html')
        
        # Validate email is not already in use by another user
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, 'Email is already in use.')
            return render(request, 'authuser/edit_profile.html')
        
        # Save updated user information to database
        user.username = username
        user.email = email
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('authuser:edit_profile')
    
    # For GET requests, don't pass any context - messages will be cleared
    return render(request, 'authuser/edit_profile.html')

@login_required
def change_password_view(request):
    """Allow users to change their account password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('authuser:change_password')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'authuser/change_password.html', {'form': form})

@login_required
def delete_account_view(request):
    """Permanently delete user account and all associated data"""
    if request.method == 'GET':
        user = request.user
        username = user.username
        
        # Delete all prediction history associated with this user
        PredictionHistory.objects.filter(user=user).delete()
        
        # Delete the user account from database
        user.delete()
        
        # Log out and redirect to home page
        logout(request)
        messages.success(request, f'Account "{username}" has been permanently deleted.')
        return redirect('home')
    
    # Invalid request method, redirect to profile page
    return redirect('authuser:edit_profile')
