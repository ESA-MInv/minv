from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from minv.inventory import models


def login_view(request):
    """ Django view to log in as a user. Logs out when the user was logged in
    before.
    """
    logout(request)
    username = password = ''
    login_error = None
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        next_ = request.POST.get('next')

        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            if next_:
                return redirect(next_)
            return redirect('root')
        else:
            login_error = True
    return render(
        request, 'minv/login.html', {
            "next": request.GET.get("next"),
            "login_error": login_error
        }
    )


def logout_view(request):
    """ Django view to log out the current user.
    """
    logout(request)
    next_ = request.GET.get("next")
    if next_:
        return redirect(next_)
    return redirect('root')


@login_required(login_url="login")
def root_view(request):
    """ The root view of the Master Inventory.
    """
    return render(
        request, "minv/root.html", {
            "collections": models.Collection.objects.all()
        }
    )
